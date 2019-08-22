# -*- encoding: utf-8
# pylint: disable=protected-access,redefined-outer-name
import io

import pytest  # type: ignore

from testlib import import_module  # pylint: disable=import-error

RESPONSE = "\n".join(("1st line", "2nd line", "3rd line"))


@pytest.fixture(scope="module")
def apache_status(request):
    yield import_module(request, "agents/plugins/apache_status")


@pytest.fixture
def response():
    return io.BytesIO(RESPONSE)


@pytest.mark.parametrize("cfg", [
    ("http", "127.0.0.1", None),
    ("http", "127.0.0.1", None, ""),
    (("http", None), "127.0.0.1", None, ""),
    {
        "protocol": "http",
        "cafile": None,
        "address": "127.0.0.1",
        "port": None,
        "instance": "",
    },
])
def test_http_cfg_versions(apache_status, cfg):
    assert apache_status._unpack(cfg) == (("http", None), "127.0.0.1", None, "", "server-status")


@pytest.mark.parametrize("cfg", [
    (("https", "/path/to/ca.pem"), "127.0.0.1", 123, ""),
    {
        "protocol": "https",
        "cafile": "/path/to/ca.pem",
        "address": "127.0.0.1",
        "port": 123,
        "instance": "",
    },
])
def test_https_cfg_versions(apache_status, cfg):
    assert apache_status._unpack(cfg) == (("https", "/path/to/ca.pem"), "127.0.0.1", 123, "",
                                          "server-status")


@pytest.mark.parametrize("cfg", [
    [(("http", None), "127.0.0.1", None, "")],
    [("http", "127.0.0.1", None, "")],
    [("http", "127.0.0.1", None)],
])
def test_agent(apache_status, cfg, response, monkeypatch, capsys):
    monkeypatch.setattr(apache_status, "get_config", lambda: {"servers": cfg, "ssl_ports": [443]})
    monkeypatch.setattr(apache_status, "get_response", lambda *args: response)
    apache_status.main()
    captured = capsys.readouterr()
    assert captured.out == ("<<<apache_status:sep(124)>>>\n" + "\n".join(
        ("127.0.0.1|None||%s" % line for line in RESPONSE.split("\n"))) + "\n")
