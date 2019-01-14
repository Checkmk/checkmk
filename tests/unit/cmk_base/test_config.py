# encoding: utf-8

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
    ("testhost", ["ip-v4"], False),
    ("testhost", ["ip-v4", "ip-v6"], False),
    ("testhost", ["ip-v6"], False),
    ("testhost", ["no-ip"], True),
])
def test_is_no_ip_host(monkeypatch, hostname, tags, result):
    monkeypatch.setattr(config, "tags_of_host", lambda h: {hostname: tags}[h])
    assert config.is_no_ip_host(hostname) == result


@pytest.mark.parametrize("hostname,tags,result,ruleset", [
    ("testhost", [], False, []),
    ("testhost", ["ip-v4"], False, [
        ('ipv6', [], config.ALL_HOSTS, {}),
    ]),
    ("testhost", ["ip-v4", "ip-v6"], False, []),
    ("testhost", ["ip-v4", "ip-v6"], True, [
        ('ipv6', [], config.ALL_HOSTS, {}),
    ]),
    ("testhost", ["ip-v6"], True, []),
    ("testhost", ["ip-v6"], True, [
        ('ipv4', [], config.ALL_HOSTS, {}),
    ]),
    ("testhost", ["ip-v6"], True, [
        ('ipv6', [], config.ALL_HOSTS, {}),
    ]),
    ("testhost", ["no-ip"], False, []),
])
def test_is_ipv6_primary_host(monkeypatch, hostname, tags, result, ruleset):
    monkeypatch.setattr(config, "all_hosts", ["%s|%s" % (hostname, "|".join(tags))])
    monkeypatch.setattr(config, "tags_of_host", lambda h: {hostname: tags}[h])
    monkeypatch.setattr(config, "primary_address_family", ruleset)
    assert config.is_ipv6_primary(hostname) == result


@pytest.mark.parametrize("result,attrs", [
    ("127.0.1.1", {}),
    ("127.0.1.1", {
        "management_address": ""
    }),
    ("127.0.0.1", {
        "management_address": "127.0.0.1"
    }),
    ("lolo", {
        "management_address": "lolo"
    }),
])
def test_management_address_of(monkeypatch, attrs, result):
    # Host IP address is 127.0.1.1
    monkeypatch.setitem(config.ipaddresses, "hostname", "127.0.1.1")

    monkeypatch.setitem(config.host_attributes, "hostname", attrs)

    assert config.management_address_of("hostname") == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", [], True),
    ("testhost", ["cmk-agent"], True),
    ("testhost", ["cmk-agent", "tcp"], True),
    ("testhost", ["snmp", "tcp"], True),
    ("testhost", ["ping"], False),
    ("testhost", ["no-agent", "no-snmp"], False),
])
def test_is_tcp_host(monkeypatch, hostname, tags, result):
    monkeypatch.setattr(config, "tags_of_host", lambda h: {hostname: tags}[h])
    assert config.is_tcp_host(hostname) == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", [], False),
    ("testhost", ["cmk-agent"], False),
    ("testhost", ["snmp", "tcp"], True),
    ("testhost", ["snmp"], True),
])
def test_is_snmp_host(monkeypatch, hostname, tags, result):
    monkeypatch.setattr(config, "tags_of_host", lambda h: {hostname: tags}[h])
    assert config.is_snmp_host(hostname) == result


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


def test_prepare_check_command_basics():
    assert config.prepare_check_command(u"args 123 -x 1 -y 2", "bla", "blub") \
        == u"args 123 -x 1 -y 2"

    assert config.prepare_check_command(["args", "123", "-x", "1", "-y", "2"], "bla", "blub") \
        == "'args' '123' '-x' '1' '-y' '2'"

    assert config.prepare_check_command(["args", "1 2 3", "-d=2", "--hallo=eins", 9], "bla", "blub") \
        == "'args' '1 2 3' '-d=2' '--hallo=eins' 9"

    with pytest.raises(NotImplementedError):
        config.prepare_check_command((1, 2), "bla", "blub")


@pytest.mark.parametrize("pw", ["abc", "123", "x'äd!?", u"aädg"])
def test_prepare_check_command_password_store(monkeypatch, pw):
    monkeypatch.setattr(config, "stored_passwords", {"pw-id": {"password": pw,}})
    assert config.prepare_check_command(["arg1", ("store", "pw-id", "--password=%s"), "arg3"], "bla", "blub") \
        == "--pwstore=2@11@pw-id 'arg1' '--password=%s' 'arg3'" % ("*" * len(pw))


def test_prepare_check_command_not_existing_password(capsys):
    assert config.prepare_check_command(["arg1", ("store", "pw-id", "--password=%s"), "arg3"], "bla", "blub") \
        == "--pwstore=2@11@pw-id 'arg1' '--password=***' 'arg3'"
    stderr = capsys.readouterr().err
    assert "The stored password \"pw-id\" used by service \"blub\" on host \"bla\"" in stderr


def test_http_proxies():
    assert config.http_proxies == {}


@pytest.mark.parametrize("http_proxy,result", [
    ("bla", None),
    (("no_proxy", None), ""),
    (("environment", None), None),
    (("global", "not_existing"), None),
    (("global", "http_blub"), "http://blub:8080"),
    (("global", "https_blub"), "https://blub:8181"),
    (("global", "socks5_authed"), "socks5://us%3Aer:s%40crit@socks.proxy:443"),
    (("url", "http://8.4.2.1:1337"), "http://8.4.2.1:1337"),
])
def test_http_proxy(http_proxy, result, monkeypatch):
    monkeypatch.setattr(
        config, "http_proxies", {
            "http_blub": {
                "ident": "blub",
                "title": "HTTP blub",
                "proxy_url": "http://blub:8080",
            },
            "https_blub": {
                "ident": "blub",
                "title": "HTTPS blub",
                "proxy_url": "https://blub:8181",
            },
            "socks5_authed": {
                "ident": "socks5",
                "title": "HTTP socks5 authed",
                "proxy_url": "socks5://us%3Aer:s%40crit@socks.proxy:443",
            },
        })

    assert config.get_http_proxy(http_proxy) == result
