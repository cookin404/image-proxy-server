import os
from io import BytesIO

import pytest
from PIL import Image

from Server import image_proxy_server

URL = 'http://example.test/image.jpg'
ORIGINAL_SIZE = (64, 48)


@pytest.fixture
def downloads(monkeypatch):
    """Replace the network fetch with a fake image and record each call."""
    calls = []

    def fake_download(url, file_path):
        calls.append(url)
        Image.new('RGB', ORIGINAL_SIZE, 'red').save(file_path, 'JPEG')

    monkeypatch.setattr(image_proxy_server, 'download_image', fake_download)
    return calls


def fetch_size(client, **params):
    response = client.get('/proxy', query_string={'url': URL, **params})
    assert response.status_code == 200
    return Image.open(BytesIO(response.data)).size


def test_resize_is_honoured_when_original_is_already_cached(client, downloads):
    assert fetch_size(client) == ORIGINAL_SIZE
    assert fetch_size(client, width=10, height=20) == (10, 20)


def test_original_is_returned_after_a_resized_request(client, downloads):
    assert fetch_size(client, width=10, height=20) == (10, 20)
    assert fetch_size(client) == ORIGINAL_SIZE


def test_each_size_is_cached_separately(client, downloads):
    assert fetch_size(client, width=10, height=20) == (10, 20)
    assert fetch_size(client, width=30, height=40) == (30, 40)
    assert fetch_size(client, width=10, height=20) == (10, 20)


def test_image_is_downloaded_only_once(client, downloads):
    fetch_size(client)
    fetch_size(client, width=10, height=20)
    fetch_size(client, width=30, height=40)
    assert downloads == [URL]


@pytest.mark.parametrize('width, height', [
    ('abc', '10'),
    ('10', '../../evil'),
    ('0', '10'),
    ('-5', '10'),
    ('100000', '10'),
])
def test_invalid_dimensions_are_rejected(client, downloads, width, height):
    response = client.get(
        '/proxy', query_string={'url': URL, 'width': width, 'height': height}
    )
    assert response.status_code == 400
    assert downloads == []


def test_assets_path_is_absolute():
    # Flask's send_file resolves relative paths against the app's root_path,
    # not the working directory, so a relative path serves nothing.
    assert os.path.isabs(image_proxy_server.PATH_TO_ASSETS)
