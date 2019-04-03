# encoding: utf-8

import pytest  # type: ignore

import cmk_base.config as config
import cmk_base.piggyback as piggyback


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
    config_cache = _setup_host(monkeypatch, hostname, tags)
    assert config.is_ipv4_host(hostname) == result
    assert config_cache.get_host_config(hostname).is_ipv4_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", [], False),
    ("testhost", ["ip-v4"], False),
    ("testhost", ["ip-v4", "ip-v6"], True),
    ("testhost", ["ip-v6"], True),
    ("testhost", ["no-ip"], False),
])
def test_is_ipv6_host(monkeypatch, hostname, tags, result):
    config_cache = _setup_host(monkeypatch, hostname, tags)
    assert config.is_ipv6_host(hostname) == result
    assert config_cache.get_host_config(hostname).is_ipv6_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", [], False),
    ("testhost", ["ip-v4"], False),
    ("testhost", ["ip-v4", "ip-v6"], True),
    ("testhost", ["ip-v6"], False),
    ("testhost", ["no-ip"], False),
])
def test_is_ipv4v6_host(monkeypatch, hostname, tags, result):
    config_cache = _setup_host(monkeypatch, hostname, tags)
    assert config.is_ipv4v6_host(hostname) == result
    assert config_cache.get_host_config(hostname).is_ipv4v6_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", ["piggyback"], True),
    ("testhost", ["no-piggyback"], False),
])
def test_is_piggyback_host(monkeypatch, hostname, tags, result):
    config_cache = _setup_host(monkeypatch, hostname, tags)
    assert config_cache.get_host_config(hostname).is_piggyback_host == result


@pytest.mark.parametrize("with_data,result", [
    (True, True),
    (False, False),
])
@pytest.mark.parametrize("hostname,tags", [
    ("testhost", []),
    ("testhost", ["auto-piggyback"]),
])
def test_is_piggyback_host_auto(monkeypatch, hostname, tags, with_data, result):
    monkeypatch.setattr(piggyback, "has_piggyback_raw_data", lambda cache_age, hostname: with_data)
    config_cache = _setup_host(monkeypatch, hostname, tags)
    assert config_cache.get_host_config(hostname).is_piggyback_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", [], False),
    ("testhost", ["ip-v4"], False),
    ("testhost", ["ip-v4", "ip-v6"], False),
    ("testhost", ["ip-v6"], False),
    ("testhost", ["no-ip"], True),
])
def test_is_no_ip_host(monkeypatch, hostname, tags, result):
    config_cache = _setup_host(monkeypatch, hostname, tags)
    assert config.is_no_ip_host(hostname) == result
    assert config_cache.get_host_config(hostname).is_no_ip_host == result


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
    monkeypatch.setattr(config, "primary_address_family", ruleset)
    config_cache = _setup_host(monkeypatch, hostname, tags)
    assert config.is_ipv6_primary(hostname) == result
    assert config_cache.get_host_config(hostname).is_ipv6_primary == result


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
    config_cache = _setup_host(monkeypatch, hostname, tags)
    assert config.is_tcp_host(hostname) == result
    assert config_cache.get_host_config(hostname).is_tcp_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", [], False),
    ("testhost", ["cmk-agent"], False),
    ("testhost", ["snmp", "tcp"], False),
    ("testhost", ["snmp", "tcp", "ping"], False),
    ("testhost", ["snmp"], False),
    ("testhost", ["no-agent", "no-snmp", "no-piggyback"], True),
    ("testhost", ["no-agent", "no-snmp"], True),
    ("testhost", ["ping"], True),
])
def test_is_ping_host(monkeypatch, hostname, tags, result):
    config_cache = _setup_host(monkeypatch, hostname, tags)
    assert config.is_ping_host(hostname) == result
    assert config_cache.get_host_config(hostname).is_ping_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", [], False),
    ("testhost", ["cmk-agent"], False),
    ("testhost", ["snmp", "tcp"], True),
    ("testhost", ["snmp"], True),
])
def test_is_snmp_host(monkeypatch, hostname, tags, result):
    config_cache = _setup_host(monkeypatch, hostname, tags)
    assert config.is_snmp_host(hostname) == result
    assert config_cache.get_host_config(hostname).is_snmp_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", [], False),
    ("testhost", ["tcp"], False),
    ("testhost", ["snmp"], False),
    ("testhost", ["cmk-agent", "snmp"], False),
    ("testhost", ["no-agent", "no-snmp"], False),
    ("testhost", ["tcp", "snmp"], True),
])
def test_is_dual_host(monkeypatch, hostname, tags, result):
    config_cache = _setup_host(monkeypatch, hostname, tags)
    assert config.is_dual_host(hostname) == result
    assert config_cache.get_host_config(hostname).is_dual_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", [], False),
    ("testhost", ["all-agents"], True),
    ("testhost", ["special-agents"], False),
    ("testhost", ["no-agent"], False),
    ("testhost", ["cmk-agent"], False),
])
def test_is_all_agents_host(monkeypatch, hostname, tags, result):
    config_cache = _setup_host(monkeypatch, hostname, tags)
    assert config.is_all_agents_host(hostname) == result
    assert config_cache.get_host_config(hostname).is_all_agents_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", [], False),
    ("testhost", ["all-agents"], False),
    ("testhost", ["special-agents"], True),
    ("testhost", ["no-agent"], False),
    ("testhost", ["cmk-agent"], False),
])
def test_is_all_special_agents_host(monkeypatch, hostname, tags, result):
    config_cache = _setup_host(monkeypatch, hostname, tags)
    assert config.is_all_special_agents_host(hostname) == result
    assert config_cache.get_host_config(hostname).is_all_special_agents_host == result


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


def _setup_host(monkeypatch, hostname, tags):
    monkeypatch.setattr(config, "all_hosts", ["%s|%s" % (hostname, "|".join(tags))])
    monkeypatch.setattr(config, "host_paths", {hostname: "/"})

    config_cache = config.get_config_cache()
    config_cache.initialize()
    return config_cache


def test_service_depends_on(monkeypatch):
    assert config.service_depends_on("test-host", "svc") == []

    monkeypatch.setattr(config, "all_hosts", ["test-host"])
    monkeypatch.setattr(config, "host_paths", {"test-host": "/"})
    monkeypatch.setattr(config, "service_dependencies", [
        ("dep1", [], config.ALL_HOSTS, ["svc1"], {}),
        ("dep2-%s", [], config.ALL_HOSTS, ["svc1-(.*)"], {}),
        ("dep-disabled", [], config.ALL_HOSTS, ["svc1"], {
            "disabled": True
        }),
    ])

    config.get_config_cache().initialize()

    assert config.service_depends_on("test-host", "svc2") == []
    assert config.service_depends_on("test-host", "svc1") == ["dep1"]
    assert config.service_depends_on("test-host", "svc1-abc") == ["dep1", "dep2-abc"]


def test_host_tags_default():
    assert isinstance(config.host_tags, dict)


def test_host_tags_of_host(monkeypatch):
    monkeypatch.setattr(config, "host_tags", {
        "test-host": {
            "tag_group": "abc",
        },
    })
    config_cache = _setup_host(monkeypatch, "test-host", ["abc"])

    cfg = config_cache.get_host_config("xyz")
    assert cfg.tag_groups == {}
    assert config_cache.tags_of_host("xyz") == {}

    cfg = config_cache.get_host_config("test-host")
    assert cfg.tag_groups == {"tag_group": "abc"}
    assert config_cache.tags_of_host("test-host") == {"tag_group": "abc"}


def test_service_tag_rules_default():
    assert isinstance(config.service_tag_rules, list)


def test_tags_of_service(monkeypatch):
    monkeypatch.setattr(config, "host_tags", {
        "test-host": {
            "tag_group": "abc",
        },
    })

    ruleset = [
        ([("tag_group1", "val1")], ["abc"], config.ALL_HOSTS, ["CPU load$"], {}),
    ]
    monkeypatch.setattr(config, "service_tag_rules", ruleset)

    config_cache = _setup_host(monkeypatch, "test-host", ["abc"])

    cfg = config_cache.get_host_config("xyz")
    assert cfg.tag_groups == {}
    assert config_cache.tags_of_service("xyz", "CPU load") == {}

    cfg = config_cache.get_host_config("test-host")
    assert cfg.tag_groups == {"tag_group": "abc"}
    assert config_cache.tags_of_service("test-host", "CPU load") == {"tag_group1": "val1"}


def test_config_cache_get_host_config():
    cache = config.ConfigCache()
    assert cache._host_configs == {}

    host_config = cache.get_host_config("xyz")
    assert isinstance(host_config, config.HostConfig)
    assert host_config is cache.get_host_config("xyz")
