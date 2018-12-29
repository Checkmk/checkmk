import socket
from pathlib2 import Path
import pytest  # type: ignore

import livestatus


@pytest.fixture()
def sock_path(monkeypatch, tmpdir):
    omd_root = Path("%s" % tmpdir)
    sock_path = omd_root / "tmp" / "run" / "live"
    monkeypatch.setenv("OMD_ROOT", "%s" % omd_root)
    # Will be fixed with pylint >2.0
    sock_path.parent.mkdir(parents=True)  # pylint: disable=no-member
    return sock_path


@pytest.mark.parametrize("query_part", [
    u"xyz\nabc",
    b"xyz\nabc",
])
def test_lqencode(query_part):
    result = livestatus.lqencode(query_part)
    assert isinstance(result, type(query_part))
    assert result == "xyzabc"


def test_livestatus_local_connection_omd_root_not_set(monkeypatch, tmpdir):
    with pytest.raises(livestatus.MKLivestatusConfigError, match="OMD_ROOT is not set"):
        livestatus.LocalConnection()


def test_livestatus_local_connection_no_socket(sock_path):
    with pytest.raises(
            livestatus.MKLivestatusSocketError, match="Cannot connect to 'unix:%s'" % sock_path):
        livestatus.LocalConnection()


def test_livestatus_local_connection_not_listening(sock_path):
    sock = socket.socket(socket.AF_UNIX)
    sock.bind("%s" % sock_path)

    with pytest.raises(
            livestatus.MKLivestatusSocketError, match="Cannot connect to 'unix:%s'" % sock_path):
        livestatus.LocalConnection()


def test_livestatus_local_connection(sock_path):
    sock = socket.socket(socket.AF_UNIX)
    sock.bind("%s" % sock_path)
    sock.listen(1)

    live = livestatus.LocalConnection()
    assert isinstance(live, livestatus.SingleSiteConnection)


@pytest.mark.parametrize("socket_url,result", [
    ("unix:/omd/sites/heute/tmp/run/live", (socket.AF_UNIX, "/omd/sites/heute/tmp/run/live")),
    ("unix:/omd/sites/heute/tmp/run/li:ve", (socket.AF_UNIX, "/omd/sites/heute/tmp/run/li:ve")),
    ("tcp:127.0.0.1:1234", (socket.AF_INET, ("127.0.0.1", 1234))),
    ("tcp:126.0.0.1:abc", None),
    ("xyz:bla", None),
])
def test_single_site_connection_socketurl(socket_url, result, monkeypatch):
    live = livestatus.SingleSiteConnection(socket_url)

    if result is None:
        with pytest.raises(livestatus.MKLivestatusConfigError, match="Invalid livestatus"):
            live._parse_socket_url(socket_url)
        return

    assert live._parse_socket_url(socket_url) == result
