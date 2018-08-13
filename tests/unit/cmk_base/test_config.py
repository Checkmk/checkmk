import pytest

import cmk_base.config as config

@pytest.fixture(autouse=True, scope="function")
def clear_config_caches(monkeypatch):
    import cmk_base
    import cmk_base.caching
    monkeypatch.setattr(cmk_base, "config_cache", cmk_base.caching.CacheManager())
    monkeypatch.setattr(cmk_base, "runtime_cache", cmk_base.caching.CacheManager())

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
     [ ( 'ipv6', [], config.ALL_HOSTS, {} ), ]),
    ("testhost", ["ip-v4", "ip-v6"], False, []),
    ("testhost", ["ip-v4", "ip-v6"], True,
     [ ( 'ipv6', [], config.ALL_HOSTS, {} ), ]),
    ("testhost", ["ip-v6"], True, []),
    ("testhost", ["ip-v6"], True,
     [ ( 'ipv4', [], config.ALL_HOSTS, {} ), ]),
    ("testhost", ["ip-v6"], True,
     [ ( 'ipv6', [], config.ALL_HOSTS, {} ), ]),
    ("testhost", ["no-ip"], False, []),
])
def test_is_ipv6_primary_host(monkeypatch, hostname, tags, result, ruleset):
    monkeypatch.setattr(config, "all_hosts", ["%s|%s" % (hostname, "|".join(tags))])
    monkeypatch.setattr(config, "tags_of_host", lambda h: {hostname: tags}[h])
    monkeypatch.setattr(config, "primary_address_family", ruleset)
    assert config.is_ipv6_primary(hostname) == result


@pytest.mark.parametrize("result,attrs", [
    ("127.0.1.1", {}),
    ("127.0.1.1", {"management_address": ""}),
    ("127.0.0.1", {"management_address": "127.0.0.1"}),
    ("lolo", {"management_address": "lolo"}),
])
def test_management_address_of(monkeypatch, attrs, result):
    # Host IP address is 127.0.1.1
    monkeypatch.setitem(config.ipaddresses, "hostname", "127.0.1.1")

    monkeypatch.setitem(config.host_attributes, "hostname", attrs)

    assert config.management_address_of("hostname") == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", [], False),
    ("testhost", ["all-agents"], True),
    ("testhost", ["special-agents"], False),
    ("testhost", ["no-agent"], False),
    ("testhost", ["cmk-agent"], False),
])
def test_is_all_agents_host(monkeypatch, hostname, tags, result):
    monkeypatch.setattr(config, "tags_of_host", lambda h: {hostname: tags}[h])
    assert config.is_all_agents_host(hostname) == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", [], False),
    ("testhost", ["all-agents"], False),
    ("testhost", ["special-agents"], True),
    ("testhost", ["no-agent"], False),
    ("testhost", ["cmk-agent"], False),
])
def test_is_all_special_agents_host(monkeypatch, hostname, tags, result):
    monkeypatch.setattr(config, "tags_of_host", lambda h: {hostname: tags}[h])
    assert config.is_all_special_agents_host(hostname) == result
