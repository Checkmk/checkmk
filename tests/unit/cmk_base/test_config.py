import pytest

import cmk_base.config as config

@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", [], True),
    ("testhost", ["ip-v4"], True),
    ("testhost", ["ip-v4", "ip-v6"], True),
    ("testhost", ["ip-v6"], False),
    ("testhost", ["no-ip"], False),
])
def test_is_ipv4_host(monkeypatch, hostname, tags, result):
    monkeypatch.setattr(config, "tags_of_host", lambda h: {hostname: tags}[h])
    assert config.is_ipv4_host(hostname) == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", [], False),
    ("testhost", ["ip-v4"],False),
    ("testhost", ["ip-v4", "ip-v6"], False),
    ("testhost", ["ip-v6"], False),
    ("testhost", ["no-ip"], True),
])
def test_is_no_ip_host(monkeypatch, hostname, tags, result):
    monkeypatch.setattr(config, "tags_of_host", lambda h: {hostname: tags}[h])
    assert config.is_no_ip_host(hostname) == result
