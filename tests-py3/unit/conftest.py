# pylint: disable=redefined-outer-name

import socket
import pytest  # type: ignore
import cmk


@pytest.fixture(autouse=True)
def patch_omd_site(monkeypatch):
    monkeypatch.setattr(cmk, "omd_site", lambda: "NO_SITE")


# Unit tests should not be executed in site.
# -> Disabled site fixture for them
@pytest.fixture(scope="session")
def site(request):
    pass


# TODO: This fixes our unit tests when executing the tests while the local
# resolver uses a search domain which uses wildcard resolution. e.g. in a
# network where mathias-kettner.de is in the domain search list and
# [anything].mathias-kettner.de resolves to an IP address.
# Clean this up once we don't have this situation anymore e.g. via VPN.
@pytest.fixture()
def fixup_ip_lookup(monkeypatch):
    # Fix IP lookup when
    def _getaddrinfo(host, port, family=None, socktype=None, proto=None, flags=None):
        if family == socket.AF_INET:
            return "0.0.0.0"
        raise NotImplementedError()

    monkeypatch.setattr(socket, "getaddrinfo", _getaddrinfo)
