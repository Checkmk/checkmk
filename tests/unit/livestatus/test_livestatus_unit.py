# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name

import errno
import socket
import ssl
from contextlib import closing

import six
import pytest  # type: ignore

import omdlib.certs as certs
import livestatus


@pytest.mark.parametrize("source, utf8str", [
    ('hi', u'hi'),
    ("há li", u"há li"),
    (u"hé ßß", u"hé ßß"),
])
def test_ensure_unicode(source, utf8str):
    assert livestatus.ensure_unicode(source) == utf8str


@pytest.mark.parametrize("source, bytestr", [
    ('hi', b'hi'),
    ("há li", b"h\xc3\xa1 li"),
    (u"hé ßß", b"h\xc3\xa9 \xc3\x9f\xc3\x9f"),
])
def test_ensure_bytestr(source, bytestr):
    assert livestatus.ensure_bytestr(source) == bytestr


@pytest.fixture
def ca(tmp_path, monkeypatch):
    p = tmp_path / "etc" / "ssl"
    return certs.CertificateAuthority(p, "ca-name")


@pytest.fixture()
def sock_path(monkeypatch, tmp_path):
    omd_root = tmp_path
    sock_path = omd_root / "tmp" / "run" / "live"
    monkeypatch.setenv("OMD_ROOT", "%s" % omd_root)
    # Will be fixed with pylint >2.0
    sock_path.parent.mkdir(parents=True)  # pylint: disable=no-member
    return sock_path


@pytest.mark.parametrize("query_part", [
    "xyz\nabc",
    u"xyz\nabc",
    b"xyz\nabc",
])
def test_lqencode(query_part):
    result = livestatus.lqencode(query_part)
    assert result == u"xyzabc"


@pytest.mark.parametrize("inp,expected_result", [
    ("ab c", u"'ab c'"),
    ("ab'c", u"'ab''c'"),
    (u"ä \nabc", u"'ä \nabc'"),
])
def test_quote_dict(inp, expected_result):
    result = livestatus.quote_dict(inp)
    assert isinstance(result, six.text_type)
    assert result == expected_result


def test_livestatus_local_connection_omd_root_not_set(monkeypatch, tmp_path):
    with pytest.raises(livestatus.MKLivestatusConfigError, match="OMD_ROOT is not set"):
        livestatus.LocalConnection()


def test_livestatus_local_connection_no_socket(sock_path):
    live = livestatus.LocalConnection()
    with pytest.raises(livestatus.MKLivestatusSocketError,
                       match="Cannot connect to 'unix:%s'" % sock_path):
        live.connect()


def test_livestatus_local_connection_not_listening(sock_path):
    sock = socket.socket(socket.AF_UNIX)
    sock.bind("%s" % sock_path)

    live = livestatus.LocalConnection()
    with pytest.raises(livestatus.MKLivestatusSocketError,
                       match="Cannot connect to 'unix:%s'" % sock_path):
        live.connect()


def test_livestatus_local_connection(sock_path):
    sock = socket.socket(socket.AF_UNIX)
    sock.bind("%s" % sock_path)
    sock.listen(1)

    live = livestatus.LocalConnection()
    assert isinstance(live, livestatus.SingleSiteConnection)


def test_livestatus_ipv4_connection():
    with closing(socket.socket(socket.AF_INET)) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # pylint: disable=no-member

        # Pick a random port
        sock.bind(("127.0.0.1", 0))  # pylint: disable=no-member
        port = sock.getsockname()[1]  # pylint: disable=no-member

        sock.listen(1)  # pylint: disable=no-member

        live = livestatus.SingleSiteConnection("tcp:127.0.0.1:%d" % port)
        live.connect()


def test_livestatus_ipv6_connection():
    with closing(socket.socket(socket.AF_INET6)) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # pylint: disable=no-member

        # Pick a random port
        try:
            sock.bind(("::1", 0))  # pylint: disable=no-member
        except socket.error as e:
            # Skip this test in case ::1 can not be bound to
            # (happened in docker container with IPv6 disabled)
            if e.errno == errno.EADDRNOTAVAIL:
                pytest.skip("Unable to bind to ::1 (%s)" % e)

        port = sock.getsockname()[1]  # pylint: disable=no-member

        sock.listen(1)  # pylint: disable=no-member

        live = livestatus.SingleSiteConnection("tcp6:::1:%d" % port)
        live.connect()


@pytest.mark.parametrize("socket_url,result", [
    ("unix:/omd/sites/heute/tmp/run/live", (socket.AF_UNIX, "/omd/sites/heute/tmp/run/live")),
    ("unix:/omd/sites/heute/tmp/run/li:ve", (socket.AF_UNIX, "/omd/sites/heute/tmp/run/li:ve")),
    ("tcp:127.0.0.1:1234", (socket.AF_INET, ("127.0.0.1", 1234))),
    ("tcp:126.0.0.1:abc", None),
    ("tcp6:::1:1234", (socket.AF_INET6, ("::1", 1234))),
    ("tcp6:::1:abc", None),
    ("xyz:bla", None),
])
def test_single_site_connection_socketurl(socket_url, result, monkeypatch):
    live = livestatus.SingleSiteConnection(socket_url)

    if result is None:
        with pytest.raises(livestatus.MKLivestatusConfigError, match="Invalid livestatus"):
            live._parse_socket_url(socket_url)
        return

    assert live._parse_socket_url(socket_url) == result


@pytest.mark.parametrize("tls", [True, False])
@pytest.mark.parametrize("verify", [True, False])
@pytest.mark.parametrize("ca_file_path", ["ca.pem", None])
def test_create_socket(tls, verify, ca, ca_file_path, monkeypatch, tmp_path):
    ca.initialize()

    ssl_dir = tmp_path / "var/ssl"
    ssl_dir.mkdir(parents=True)
    with ssl_dir.joinpath("ca-certificates.crt").open(mode="w", encoding="utf-8") as f:  # pylint: disable=no-member
        f.write(ca.ca_path.joinpath("ca.pem").open(encoding="utf-8").read())

    monkeypatch.setenv("OMD_ROOT", str(tmp_path))

    if ca_file_path is not None:
        ca_file_path = "%s/%s" % (ca.ca_path, ca_file_path)

    live = livestatus.SingleSiteConnection("unix:/tmp/xyz",
                                           tls=tls,
                                           verify=verify,
                                           ca_file_path=ca_file_path)

    if ca_file_path is None:
        ca_file_path = tmp_path / "var/ssl/ca-certificates.crt"

    sock = live._create_socket(socket.AF_INET)

    if not tls:
        assert isinstance(sock, socket.socket)
        assert not isinstance(sock, ssl.SSLSocket)
        return

    assert isinstance(sock, ssl.SSLSocket)
    assert sock.context.verify_mode == (ssl.CERT_REQUIRED if verify else ssl.CERT_NONE)
    assert len(sock.context.get_ca_certs()) == 1
    assert live.tls_ca_file_path == str(ca_file_path)


def test_create_socket_not_existing_ca_file():
    live = livestatus.SingleSiteConnection("unix:/tmp/xyz",
                                           tls=True,
                                           verify=True,
                                           ca_file_path="/x/y/z.pem")
    with pytest.raises(livestatus.MKLivestatusConfigError, match="No such file or"):
        live._create_socket(socket.AF_INET)


def test_create_socket_no_cert(tmp_path):
    open(str(tmp_path / "z.pem"), "wb")
    live = livestatus.SingleSiteConnection("unix:/tmp/xyz",
                                           tls=True,
                                           verify=True,
                                           ca_file_path=str(tmp_path / "z.pem"))
    with pytest.raises(livestatus.MKLivestatusConfigError,
                       match="(unknown error|no certificate or crl found)"):
        live._create_socket(socket.AF_INET)
