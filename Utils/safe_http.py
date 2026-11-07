import ipaddress
import socket

import requests
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from urllib3.util.connection import create_connection

MAX_REDIRECTS = 5

# Transition prefixes that embed an IPv4 address, which is_global cannot see into.
TRANSITION_NETWORKS = (
    ipaddress.ip_network('64:ff9b::/96'),
    ipaddress.ip_network('2002::/16'),
)


class BlockedURLError(Exception):
    """The URL points at something the proxy must not contact."""


def is_public_address(address):
    ip = ipaddress.ip_address(address.split('%')[0])
    ip = getattr(ip, 'ipv4_mapped', None) or ip

    return (
        ip.is_global
        and not ip.is_multicast
        and not ip.is_reserved
        and not any(ip in network for network in TRANSITION_NETWORKS)
    )


def resolve_public_address(host):
    # Reject the host if any record is internal, not just the one we would use.
    infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    addresses = [info[4][0] for info in infos]

    if not all(is_public_address(address) for address in addresses):
        raise BlockedURLError(f'{host} resolves to a non-public address')

    return min(addresses, key=lambda address: ':' in address)  # prefer IPv4


class PublicOnlyConnectionMixin:
    # The check runs here rather than before the request, so that the address
    # that was checked is the one connected to (no DNS rebinding window), and
    # every redirect hop goes through it. The host name stays untouched for the
    # Host header, SNI and certificate verification.
    def _new_conn(self):
        return create_connection(
            (resolve_public_address(self.host), self.port),
            self.timeout,
            source_address=self.source_address,
            socket_options=self.socket_options,
        )


class PublicOnlyHTTPConnection(PublicOnlyConnectionMixin, HTTPConnection):
    pass


class PublicOnlyHTTPSConnection(PublicOnlyConnectionMixin, HTTPSConnection):
    pass


class PublicOnlyHTTPPool(HTTPConnectionPool):
    ConnectionCls = PublicOnlyHTTPConnection


class PublicOnlyHTTPSPool(HTTPSConnectionPool):
    ConnectionCls = PublicOnlyHTTPSConnection


class PublicOnlyAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        super().init_poolmanager(*args, **kwargs)
        self.poolmanager.pool_classes_by_scheme = {
            'http': PublicOnlyHTTPPool,
            'https': PublicOnlyHTTPSPool,
        }


def create_session():
    session = requests.Session()
    session.trust_env = False  # a proxy from the environment would skip the check
    session.max_redirects = MAX_REDIRECTS
    session.mount('http://', PublicOnlyAdapter())
    session.mount('https://', PublicOnlyAdapter())
    return session
