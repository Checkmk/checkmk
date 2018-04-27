import pytest

import cmk_base.config as config
import cmk_base.rulesets as rulesets

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


@pytest.mark.parametrize("hostname,tags,result,ruleset", [
    ("testhost", [], False, []),
    ("testhost", ["ip-v4"], False,
     [ ( 'ipv6', [], rulesets.ALL_HOSTS, {} ), ]),
    ("testhost", ["ip-v4", "ip-v6"], False, []),
    ("testhost", ["ip-v4", "ip-v6"], True,
     [ ( 'ipv6', [], rulesets.ALL_HOSTS, {} ), ]),
    ("testhost", ["ip-v6"], True, []),
    ("testhost", ["ip-v6"], True,
     [ ( 'ipv4', [], rulesets.ALL_HOSTS, {} ), ]),
    ("testhost", ["ip-v6"], True,
     [ ( 'ipv6', [], rulesets.ALL_HOSTS, {} ), ]),
    ("testhost", ["no-ip"], False, []),
])
def test_is_ipv6_primary_host(monkeypatch, hostname, tags, result, ruleset):
    monkeypatch.setattr(config, "all_hosts", ["%s|%s" % (hostname, "|".join(tags))])
    monkeypatch.setattr(config, "tags_of_host", lambda h: {hostname: tags}[h])
    monkeypatch.setattr(config, "primary_address_family", ruleset)
    assert config.is_ipv6_primary(hostname) == result
