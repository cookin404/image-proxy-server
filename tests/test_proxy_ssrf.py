import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO

import pytest
from PIL import Image

from Utils import image_utils

PUBLIC_IP = '93.184.216.34'


def jpeg_bytes():
    buffer = BytesIO()
    Image.new('RGB', (8, 8), 'blue').save(buffer, 'JPEG')
    return buffer.getvalue()


class Upstream:
    """Real HTTP server on loopback, standing in for both sides of the proxy."""

    def __init__(self):
        self.hits = []
        upstream = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                upstream.hits.append(self.path)
                status, headers, body = upstream.route(self.path)
                self.send_response(status)
                for name, value in headers.items():
                    self.send_header(name, value)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.port = self.server.server_address[1]
        self.routes = {}
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def route(self, path):
        return self.routes.get(path, (404, {}, b''))

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def upstream():
    server = Upstream()
    yield server
    server.close()


@pytest.fixture
def fake_dns(monkeypatch):
    """Map host names to addresses; anything else resolves for real."""
    records = {}
    real_getaddrinfo = socket.getaddrinfo

    def getaddrinfo(host, port, *args, **kwargs):
        if host in records:
            return [
                (socket.AF_INET6 if ':' in ip else socket.AF_INET,
                 socket.SOCK_STREAM, 6, '', (ip, port))
                for ip in records[host]
            ]
        return real_getaddrinfo(host, port, *args, **kwargs)

    monkeypatch.setattr(socket, 'getaddrinfo', getaddrinfo)
    return records


@pytest.fixture
def public_upstream(upstream, fake_dns, monkeypatch):
    """Let the test server pose as a public host: public.test -> loopback."""
    from Utils import safe_http

    real_resolve = safe_http.resolve_public_address

    def resolve(host):
        return '127.0.0.1' if host == 'public.test' else real_resolve(host)

    monkeypatch.setattr(safe_http, 'resolve_public_address', resolve)
    return upstream


def proxy(client, url):
    return client.get('/proxy', query_string={'url': url})


@pytest.mark.parametrize('host', [
    '127.0.0.1',
    'localhost',
    '[::1]',
    '[::ffff:127.0.0.1]',
    '2130706433',
    '0.0.0.0',
])
def test_loopback_is_never_contacted(client, upstream, host):
    upstream.routes['/secret'] = (200, {}, jpeg_bytes())

    response = proxy(client, f'http://{host}:{upstream.port}/secret')

    assert response.status_code == 400
    assert upstream.hits == []


@pytest.mark.parametrize('address', [
    '10.0.0.1',
    '172.16.0.1',
    '192.168.1.1',
    '169.254.169.254',
    '100.64.0.1',
    '224.0.0.1',
    '240.0.0.1',
    'fe80::1',
    'fc00::1',
    '::ffff:10.0.0.1',
    '64:ff9b::7f00:1',
    '2002:7f00:1::',
    'ff02::1',
])
def test_hostname_resolving_to_internal_address_is_blocked(client, fake_dns, address):
    fake_dns['internal.test'] = [address]

    assert proxy(client, 'http://internal.test/').status_code == 400


def test_host_with_one_internal_address_is_blocked(client, fake_dns):
    fake_dns['mixed.test'] = [PUBLIC_IP, '10.0.0.1']

    assert proxy(client, 'http://mixed.test/').status_code == 400


@pytest.mark.parametrize('url', [
    'file:///etc/passwd',
    'ftp://example.test/image.jpg',
    'gopher://example.test/',
    'no-scheme',
])
def test_other_schemes_are_blocked(client, url):
    assert proxy(client, url).status_code == 400


def test_public_image_is_proxied(client, public_upstream):
    public_upstream.routes['/a.jpg'] = (200, {}, jpeg_bytes())

    response = proxy(client, f'http://public.test:{public_upstream.port}/a.jpg')

    assert response.status_code == 200
    assert response.data == jpeg_bytes()


def test_redirect_to_public_host_is_followed(client, public_upstream):
    port = public_upstream.port
    public_upstream.routes['/a'] = (
        302, {'Location': f'http://public.test:{port}/b.jpg'}, b''
    )
    public_upstream.routes['/b.jpg'] = (200, {}, jpeg_bytes())

    assert proxy(client, f'http://public.test:{port}/a').status_code == 200


def test_redirect_to_internal_host_is_blocked(client, public_upstream):
    port = public_upstream.port
    public_upstream.routes['/a'] = (
        302, {'Location': f'http://127.0.0.1:{port}/secret'}, b''
    )
    public_upstream.routes['/secret'] = (200, {}, jpeg_bytes())

    response = proxy(client, f'http://public.test:{port}/a')

    assert response.status_code == 400
    assert public_upstream.hits == ['/a']


def test_redirect_loop_gives_up(client, public_upstream):
    url = f'http://public.test:{public_upstream.port}/loop'
    public_upstream.routes['/loop'] = (302, {'Location': url}, b'')

    assert proxy(client, url).status_code == 500


def test_environment_proxy_is_ignored(client, public_upstream, monkeypatch):
    # A proxy would resolve the host itself and bypass the address check.
    monkeypatch.setenv('HTTP_PROXY', 'http://127.0.0.1:9')
    public_upstream.routes['/a.jpg'] = (200, {}, jpeg_bytes())

    url = f'http://public.test:{public_upstream.port}/a.jpg'

    assert proxy(client, url).status_code == 200


def test_non_image_response_is_not_returned_or_cached(
    client, public_upstream, assets_dir
):
    public_upstream.routes['/config'] = (200, {}, b'{"password": "hunter2"}')

    response = proxy(client, f'http://public.test:{public_upstream.port}/config')

    assert response.status_code == 500
    assert b'hunter2' not in response.data
    assert list(assets_dir.iterdir()) == []


def test_oversized_download_is_aborted_and_not_cached(
    client, public_upstream, assets_dir, monkeypatch
):
    monkeypatch.setattr(image_utils, 'MAX_DOWNLOAD_BYTES', 100)
    public_upstream.routes['/big.jpg'] = (200, {}, jpeg_bytes())

    response = proxy(client, f'http://public.test:{public_upstream.port}/big.jpg')

    assert response.status_code == 500
    assert list(assets_dir.iterdir()) == []


def test_download_deadline_aborts_slow_response(
    client, public_upstream, assets_dir, monkeypatch
):
    monkeypatch.setattr(image_utils, 'DOWNLOAD_DEADLINE_SECONDS', 0)
    public_upstream.routes['/slow.jpg'] = (200, {}, jpeg_bytes())

    response = proxy(client, f'http://public.test:{public_upstream.port}/slow.jpg')

    assert response.status_code == 500
    assert list(assets_dir.iterdir()) == []


def test_requests_carry_a_timeout(client, public_upstream, monkeypatch):
    seen = {}
    real_get = image_utils.create_session().__class__.get

    def spy(self, url, **kwargs):
        seen.update(kwargs)
        return real_get(self, url, **kwargs)

    monkeypatch.setattr('requests.Session.get', spy)
    public_upstream.routes['/a.jpg'] = (200, {}, jpeg_bytes())

    proxy(client, f'http://public.test:{public_upstream.port}/a.jpg')

    assert seen['timeout'] == image_utils.REQUEST_TIMEOUT
