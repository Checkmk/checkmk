# encoding: utf-8
# pylint: disable=redefined-outer-name

import pytest  # type: ignore
from testlib.base import Scenario

from cmk.utils.rulesets.ruleset_matcher import RulesetMatchObject
import cmk
import cmk.utils.paths
import cmk_base.config as config
import cmk_base.piggyback as piggyback
import cmk_base.check_api as check_api


def test_all_configured_realhosts(monkeypatch):
    ts = Scenario(site_id="site1")
    ts.add_host("real1", ["site:site1"])
    ts.add_host("real2", ["site:site2"])
    ts.add_host("real3", [])
    ts.add_cluster("cluster1", ["site:site1"], nodes=["node1"])
    ts.add_cluster("cluster2", ["site:site2"], nodes=["node2"])
    ts.add_cluster("cluster3", [], nodes=["node3"])

    config_cache = ts.apply(monkeypatch)
    assert config_cache.all_configured_clusters() == set(["cluster1", "cluster2", "cluster3"])
    assert config_cache.all_configured_realhosts() == set(["real1", "real2", "real3"])
    assert config_cache.all_configured_hosts() == set(
        ["cluster1", "cluster2", "cluster3", "real1", "real2", "real3"])


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", [], True),
    ("testhost", ["ip-v4"], True),
    ("testhost", ["ip-v4", "ip-v6"], True),
    ("testhost", ["ip-v6"], False),
    ("testhost", ["no-ip"], False),
])
def test_is_ipv4_host(monkeypatch, hostname, tags, result):
    config_cache = Scenario().add_host(hostname, tags).apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_ipv4_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", [], False),
    ("testhost", ["ip-v4"], False),
    ("testhost", ["ip-v4", "ip-v6"], True),
    ("testhost", ["ip-v6"], True),
    ("testhost", ["no-ip"], False),
])
def test_is_ipv6_host(monkeypatch, hostname, tags, result):
    config_cache = Scenario().add_host(hostname, tags).apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_ipv6_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", [], False),
    ("testhost", ["ip-v4"], False),
    ("testhost", ["ip-v4", "ip-v6"], True),
    ("testhost", ["ip-v6"], False),
    ("testhost", ["no-ip"], False),
])
def test_is_ipv4v6_host(monkeypatch, hostname, tags, result):
    config_cache = Scenario().add_host(hostname, tags).apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_ipv4v6_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", ["piggyback"], True),
    ("testhost", ["no-piggyback"], False),
])
def test_is_piggyback_host(monkeypatch, hostname, tags, result):
    config_cache = Scenario().add_host(hostname, tags).apply(monkeypatch)
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
    config_cache = Scenario().add_host(hostname, tags).apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_piggyback_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", [], False),
    ("testhost", ["ip-v4"], False),
    ("testhost", ["ip-v4", "ip-v6"], False),
    ("testhost", ["ip-v6"], False),
    ("testhost", ["no-ip"], True),
])
def test_is_no_ip_host(monkeypatch, hostname, tags, result):
    config_cache = Scenario().add_host(hostname, tags).apply(monkeypatch)
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
    ts = Scenario().add_host(hostname, tags)
    ts.set_ruleset("primary_address_family", ruleset)
    config_cache = ts.apply(monkeypatch)
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
def test_host_config_management_address(monkeypatch, attrs, result):
    ts = Scenario().add_host("hostname")
    ts.set_option("ipaddresses", {"hostname": "127.0.1.1"})
    ts.set_option("host_attributes", {"hostname": attrs})
    config_cache = ts.apply(monkeypatch)

    assert config_cache.get_host_config("hostname").management_address == result


@pytest.mark.parametrize("attrs,result", [
    ({}, ([], [])),
    ({
        "additional_ipv4addresses": ["10.10.10.10"],
        "additional_ipv6addresses": ["::3"],
    }, (["10.10.10.10"], ["::3"])),
])
def test_host_config_additional_ipaddresses(monkeypatch, attrs, result):
    ts = Scenario().add_host("hostname")
    ts.set_option("ipaddresses", {"hostname": "127.0.1.1"})
    ts.set_option("host_attributes", {"hostname": attrs})
    config_cache = ts.apply(monkeypatch)

    assert config_cache.get_host_config("hostname").additional_ipaddresses == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", [], True),
    ("testhost", ["cmk-agent"], True),
    ("testhost", ["cmk-agent", "tcp"], True),
    ("testhost", ["snmp", "tcp"], True),
    ("testhost", ["ping"], False),
    ("testhost", ["no-agent", "no-snmp"], False),
])
def test_is_tcp_host(monkeypatch, hostname, tags, result):
    config_cache = Scenario().add_host(hostname, tags).apply(monkeypatch)
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
    config_cache = Scenario().add_host(hostname, tags).apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_ping_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", [], False),
    ("testhost", ["cmk-agent"], False),
    ("testhost", ["snmp", "tcp"], True),
    ("testhost", ["snmp"], True),
])
def test_is_snmp_host(monkeypatch, hostname, tags, result):
    config_cache = Scenario().add_host(hostname, tags).apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_snmp_host == result


def test_is_not_usewalk_host(monkeypatch):
    config_cache = Scenario().add_host("xyz", ["abc"]).apply(monkeypatch)
    assert config_cache.get_host_config("xyz").is_usewalk_host is False


def test_is_usewalk_host(monkeypatch):
    ts = Scenario()
    ts.add_host("xyz", ["abc"])
    ts.set_ruleset("usewalk_hosts", [
        (["xyz"], config.ALL_HOSTS, {}),
    ])

    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config("xyz").is_usewalk_host is False


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", [], False),
    ("testhost", ["tcp"], False),
    ("testhost", ["snmp"], False),
    ("testhost", ["cmk-agent", "snmp"], False),
    ("testhost", ["no-agent", "no-snmp"], False),
    ("testhost", ["tcp", "snmp"], True),
])
def test_is_dual_host(monkeypatch, hostname, tags, result):
    config_cache = Scenario().add_host(hostname, tags).apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_dual_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", [], False),
    ("testhost", ["all-agents"], True),
    ("testhost", ["special-agents"], False),
    ("testhost", ["no-agent"], False),
    ("testhost", ["cmk-agent"], False),
])
def test_is_all_agents_host(monkeypatch, hostname, tags, result):
    config_cache = Scenario().add_host(hostname, tags).apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_all_agents_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", [], False),
    ("testhost", ["all-agents"], False),
    ("testhost", ["special-agents"], True),
    ("testhost", ["no-agent"], False),
    ("testhost", ["cmk-agent"], False),
])
def test_is_all_special_agents_host(monkeypatch, hostname, tags, result):
    config_cache = Scenario().add_host(hostname, tags).apply(monkeypatch)
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


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", 6556),
    ("testhost2", 1337),
])
def test_host_config_agent_port(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset("agent_ports", [
        (1337, [], ["testhost2"], {}),
    ])
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).agent_port == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", 5.0),
    ("testhost2", 12.0),
])
def test_host_config_tcp_connect_timeout(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset("tcp_connect_timeouts", [
        (12.0, [], ["testhost2"], {}),
    ])
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).tcp_connect_timeout == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", {
        'use_regular': 'disable',
        'use_realtime': 'enforce'
    }),
    ("testhost2", {
        'use_regular': 'enforce',
        'use_realtime': 'disable'
    }),
])
def test_host_config_agent_encryption(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset("agent_encryption", [
        ({
            'use_regular': 'enforce',
            'use_realtime': 'disable'
        }, [], ["testhost2"], {}),
    ])
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).agent_encryption == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", None),
    ("testhost2", cmk.__version__),
])
def test_host_config_agent_target_version(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset("check_mk_agent_target_versions", [
        ("site", [], ["testhost2"], {}),
    ])
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).agent_target_version == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", None),
    ("testhost2", "echo 1"),
])
def test_host_config_datasource_program(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset("datasource_programs", [
        ("echo 1", [], ["testhost2"], {}),
    ])
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).datasource_program == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", []),
    ("testhost2", [
        ("abc", {
            "param1": 1
        }),
        ("xyz", {
            "param2": 1
        }),
    ]),
])
def test_host_config_special_agents(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_option(
        "special_agents", {
            "abc": [({
                "param1": 1
            }, [], ["testhost2"], {}),],
            "xyz": [({
                "param2": 1
            }, [], ["testhost2"], {}),],
        })
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).special_agents == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", None),
    ("testhost2", ["127.0.0.1"]),
])
def test_host_config_only_from(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_option(
        "agent_config", {
            "only_from": [
                ([
                    "127.0.0.1",
                ], [], ["testhost2"], {}),
                ([
                    "127.0.0.2",
                ], [], ["testhost2"], {}),
            ],
        })
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).only_from == result


@pytest.mark.parametrize("hostname,core_name,result", [
    ("testhost1", "cmc", None),
    ("testhost2", "cmc", "command1"),
    ("testhost3", "cmc", "smart"),
    ("testhost3", "nagios", "ping"),
])
def test_host_config_explicit_check_command(monkeypatch, hostname, core_name, result):
    ts = Scenario().add_host(hostname)
    ts.set_option("monitoring_core", core_name)
    ts.set_option(
        "host_check_commands",
        [
            ("command1", [], ["testhost2"], {}),
            ("command2", [], ["testhost2"], {}),
            ("smart", [], ["testhost3"], {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).explicit_check_command == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", {}),
    ("testhost2", {
        "ding": 1,
        "dong": 1
    }),
])
def test_host_config_ping_levels(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset("ping_levels", [
        ({
            "ding": 1,
        }, [], ["testhost2"], {}),
        ({
            "ding": 3,
        }, [], ["testhost2"], {}),
        ({
            "dong": 1,
        }, [], ["testhost2"], {}),
    ])
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).ping_levels == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", []),
    ("testhost2", ["icon1", "icon2"]),
])
def test_host_config_icons_and_actions(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset("host_icons_and_actions", [
        ("icon1", [], ["testhost2"], {}),
        ("icon1", [], ["testhost2"], {}),
        ("icon2", [], ["testhost2"], {}),
    ])
    config_cache = ts.apply(monkeypatch)
    assert sorted(config_cache.get_host_config(hostname).icons_and_actions) == sorted(result)


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", {}),
    ("testhost2", {
        '_CUSTOM': ['value1'],
        'dingdong': ['value1']
    }),
])
def test_host_config_extra_host_attributes(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_option(
        "extra_host_conf", {
            "dingdong": [
                ([
                    "value1",
                ], [], ["testhost2"], {}),
                ([
                    "value2",
                ], [], ["testhost2"], {}),
            ],
            "_custom": [
                ([
                    "value1",
                ], [], ["testhost2"], {}),
                ([
                    "value2",
                ], [], ["testhost2"], {}),
            ],
        })
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).extra_host_attributes == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", {}),
    ("testhost2", {
        'value1': 1,
        'value2': 2,
    }),
])
def test_host_config_inventory_parameters(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_option("inv_parameters", {
        "if": [
            ({
                "value1": 1,
            }, [], ["testhost2"], {}),
            ({
                "value2": 2,
            }, [], ["testhost2"], {}),
        ],
    })
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).inventory_parameters("if") == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", {
        'check_interval': None,
        'inventory_check_do_scan': True,
        'severity_unmonitored': 1,
        'severity_vanished': 0,
    }),
    ("testhost2", {
        "check_interval": 1,
    }),
])
def test_host_config_discovery_check_parameters(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_option(
        "periodic_discovery",
        [
            ({
                "check_interval": 1,
            }, [], ["testhost2"], {}),
            ({
                "check_interval": 2,
            }, [], ["testhost2"], {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).discovery_check_parameters == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", []),
    ("testhost2", [
        ("abc", {
            "param1": 1
        }),
        ("xyz", {
            "param2": 1
        }),
    ]),
])
def test_host_config_inventory_export_hooks(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_option(
        "inv_exports", {
            "abc": [({
                "param1": 1
            }, [], ["testhost2"], {}),],
            "xyz": [({
                "param2": 1
            }, [], ["testhost2"], {}),],
        })
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).inventory_export_hooks == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", {}),
    ("testhost2", {
        'value1': 1,
        'value2': 2,
    }),
])
def test_host_config_notification_plugin_parameters(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_option(
        "notification_parameters", {
            "mail": [
                ({
                    "value1": 1,
                }, [], ["testhost2"], {}),
                ({
                    "value1": 2,
                    "value2": 2,
                }, [], ["testhost2"], {}),
            ],
        })
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).notification_plugin_parameters("mail") == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", []),
    ("testhost2", [
        (
            "abc",
            [{
                "param1": 1
            }, {
                "param2": 2
            }],
        ),
        ("xyz", [
            {
                "param2": 1
            },
        ]),
    ]),
])
def test_host_config_active_checks(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_option(
        "active_checks", {
            "abc": [
                ({
                    "param1": 1
                }, [], ["testhost2"], {}),
                ({
                    "param2": 2
                }, [], ["testhost2"], {}),
            ],
            "xyz": [({
                "param2": 1
            }, [], ["testhost2"], {}),],
        })
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).active_checks == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", []),
    ("testhost2", [{
        "param1": 1
    }, {
        "param2": 2
    }]),
])
def test_host_config_custom_checks(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset("custom_checks", [
        ({
            "param1": 1
        }, [], ["testhost2"], {}),
        ({
            "param2": 2
        }, [], ["testhost2"], {}),
    ])
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).custom_checks == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", []),
    ("testhost2", [
        ('checkgroup', 'checktype1', 'item1', {
            'param1': 1
        }),
        ('checkgroup', 'checktype2', 'item2', {
            'param2': 2
        }),
    ]),
])
def test_host_config_static_checks(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_option(
        "static_checks", {
            "checkgroup": [
                (("checktype1", "item1", {
                    "param1": 1
                }), [], ["testhost2"], {}),
                (("checktype2", "item2", {
                    "param2": 2
                }), [], ["testhost2"], {}),
            ],
        })
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).static_checks == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", ["check_mk"]),
    ("testhost2", ["dingdong"]),
])
def test_host_config_hostgroups(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset("host_groups", [
        ("dingdong", [], ["testhost2"], {}),
    ])
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).hostgroups == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", []),
    ("testhost2", ["dingdong"]),
])
def test_host_config_contactgroups(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset("host_contactgroups", [
        ("dingdong", [], ["testhost2"], {}),
    ])
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).contactgroups == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", None),
    ("testhost2", {
        "1": 1
    }),
])
def test_host_config_rrd_config(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset("cmc_host_rrd_config", [
        ({
            "1": 1
        }, [], ["testhost2"], {}),
        ({
            "2": 2
        }, [], ["testhost2"], {}),
    ])
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).rrd_config == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", {}),
    ("testhost2", {
        'empty_output': 1
    }),
])
def test_host_config_exit_code_spec_overall(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset("check_mk_exit_status", [
        ({
            "overall": {
                "empty_output": 1
            },
            "individual": {
                "snmp": {
                    "empty_output": 4
                }
            },
        }, [], ["testhost2"], {}),
    ])
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).exit_code_spec() == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", {}),
    ("testhost2", {
        'empty_output': 4
    }),
])
def test_host_config_exit_code_spec_individual(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset("check_mk_exit_status", [
        ({
            "overall": {
                "empty_output": 1
            },
            "individual": {
                "snmp": {
                    "empty_output": 4
                }
            },
        }, [], ["testhost2"], {}),
    ])
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).exit_code_spec(data_source_id="snmp") == result


@pytest.mark.parametrize("hostname,version,result", [
    ("testhost1", 2, None),
    ("testhost2", 2, "bla"),
    ("testhost2", 3, ('noAuthNoPriv', 'v3')),
    ("testhost3", 2, "bla"),
    ("testhost3", 3, None),
    ("testhost4", 2, None),
    ("testhost4", 3, ('noAuthNoPriv', 'v3')),
])
def test_host_config_snmp_credentials_of_version(monkeypatch, hostname, version, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset("snmp_communities", [
        ("bla", [], ["testhost2", "testhost3"], {}),
        (('noAuthNoPriv', 'v3'), [], ["testhost2", "testhost4"], {}),
    ])
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).snmp_credentials_of_version(version) == result


@pytest.mark.parametrize("hostname,section_name,result", [
    ("testhost1", "uptime", None),
    ("testhost2", "uptime", None),
    ("testhost1", "snmp_uptime", None),
    ("testhost2", "snmp_uptime", 4),
])
def test_host_config_snmp_check_interval(monkeypatch, hostname, section_name, result):
    config.load_checks(check_api.get_check_api_context, ["checks/uptime", "checks/snmp_uptime"])
    ts = Scenario().add_host(hostname)
    ts.set_ruleset("snmp_check_interval", [
        (("snmp_uptime", 4), [], ["testhost2"], {}),
    ])
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).snmp_check_interval(section_name) == result


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


def test_service_depends_on_unknown_host():
    assert config.service_depends_on("test-host", "svc") == []


def test_service_depends_on(monkeypatch):
    ts = Scenario().add_host("test-host", tags=[])
    ts.set_ruleset("service_dependencies", [
        ("dep1", [], config.ALL_HOSTS, ["svc1"], {}),
        ("dep2-%s", [], config.ALL_HOSTS, ["svc1-(.*)"], {}),
        ("dep-disabled", [], config.ALL_HOSTS, ["svc1"], {
            "disabled": True
        }),
    ])
    ts.apply(monkeypatch)

    assert config.service_depends_on("test-host", "svc2") == []
    assert config.service_depends_on("test-host", "svc1") == ["dep1"]
    assert config.service_depends_on("test-host", "svc1-abc") == ["dep1", "dep2-abc"]


@pytest.fixture()
def cluster_config(monkeypatch):
    ts = Scenario().add_host("node1").add_host("host1")
    ts.add_cluster("cluster1", nodes=["node1"])
    return ts.apply(monkeypatch)


def test_host_config_is_cluster(cluster_config):
    assert cluster_config.get_host_config("node1").is_cluster is False
    assert cluster_config.get_host_config("host1").is_cluster is False
    assert cluster_config.get_host_config("cluster1").is_cluster is True


def test_host_config_part_of_clusters(cluster_config):
    assert cluster_config.get_host_config("node1").part_of_clusters == ["cluster1"]
    assert cluster_config.get_host_config("host1").part_of_clusters == []
    assert cluster_config.get_host_config("cluster1").part_of_clusters == []


def test_host_config_nodes(cluster_config):
    assert cluster_config.get_host_config("node1").nodes is None
    assert cluster_config.get_host_config("host1").nodes is None
    assert cluster_config.get_host_config("cluster1").nodes == ["node1"]


def test_host_config_parents(cluster_config):
    assert cluster_config.get_host_config("node1").parents == []
    assert cluster_config.get_host_config("host1").parents == []
    # TODO: Move cluster/node parent handling to HostConfig
    #assert cluster_config.get_host_config("cluster1").parents == ["node1"]
    assert cluster_config.get_host_config("cluster1").parents == []


def test_host_tags_default():
    assert isinstance(config.host_tags, dict)


def test_host_tags_of_host(monkeypatch):
    ts = Scenario()
    ts.add_host("test-host", ["abc"])
    ts.set_option("host_tags", {
        "test-host": {
            "tag_group": "abc",
        },
    })
    config_cache = ts.apply(monkeypatch)

    cfg = config_cache.get_host_config("xyz")
    assert cfg.tag_groups == {}
    assert config_cache.tags_of_host("xyz") == {}

    cfg = config_cache.get_host_config("test-host")
    assert cfg.tag_groups == {"tag_group": "abc"}
    assert config_cache.tags_of_host("test-host") == {"tag_group": "abc"}


def test_service_tag_rules_default():
    assert isinstance(config.service_tag_rules, list)


def test_tags_of_service(monkeypatch):
    ts = Scenario()
    ts.set_option("host_tags", {
        "test-host": {
            "tag_group": "abc",
        },
    })

    ts.set_ruleset("service_tag_rules", [
        ([("tag_group1", "val1")], ["abc"], config.ALL_HOSTS, ["CPU load$"], {}),
    ])

    ts.add_host("test-host", ["abc"])
    config_cache = ts.apply(monkeypatch)

    cfg = config_cache.get_host_config("xyz")
    assert cfg.tag_groups == {}
    assert config_cache.tags_of_service("xyz", "CPU load") == {}

    cfg = config_cache.get_host_config("test-host")
    assert cfg.tag_groups == {"tag_group": "abc"}
    assert config_cache.tags_of_service("test-host", "CPU load") == {"tag_group1": "val1"}


def test_host_label_rules_default():
    assert isinstance(config.host_label_rules, list)


def test_host_config_labels(monkeypatch):
    ts = Scenario()
    ts.set_option("host_labels", {
        "test-host": {
            "explicit": "ding",
        },
    })

    ts.set_ruleset("host_label_rules", [
        ({
            "from-rule": "rule1"
        }, ["abc"], config.ALL_HOSTS, {}),
        ({
            "from-rule2": "rule2"
        }, ["abc"], config.ALL_HOSTS, {}),
    ])

    ts.add_host("test-host", ["abc"])

    config_cache = ts.apply(monkeypatch)

    cfg = config_cache.get_host_config("xyz")
    assert cfg.labels == {}

    cfg = config_cache.get_host_config("test-host")
    assert cfg.labels == {
        "explicit": "ding",
        "from-rule": "rule1",
        "from-rule2": "rule2",
    }
    assert cfg.label_sources == {
        "explicit": "explicit",
        "from-rule": "ruleset",
        "from-rule2": "ruleset",
    }


def test_host_labels_of_host_discovered_labels(monkeypatch, tmp_path):
    ts = Scenario().add_host("test-host", ["abc"])

    monkeypatch.setattr(cmk.utils.paths, "discovered_host_labels_dir", tmp_path)
    host_file = (tmp_path / "test-host").with_suffix(".mk")
    with host_file.open(mode="wb") as f:
        f.write(repr({u"äzzzz": u"eeeeez"}) + "\n")

    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config("test-host").labels == {u"äzzzz": u"eeeeez"}
    assert config_cache.get_host_config("test-host").label_sources == {u"äzzzz": u"discovered"}


def test_service_label_rules_default():
    assert isinstance(config.service_label_rules, list)


def test_labels_of_service(monkeypatch):
    ts = Scenario()
    ts.set_ruleset("service_label_rules", [
        ({
            "label1": "val1"
        }, ["abc"], config.ALL_HOSTS, ["CPU load$"], {}),
        ({
            "label2": "val2"
        }, ["abc"], config.ALL_HOSTS, ["CPU load$"], {}),
    ])

    ts.add_host("test-host", ["abc"])
    config_cache = ts.apply(monkeypatch)

    assert config_cache.labels_of_service("xyz", "CPU load") == {}
    assert config_cache.label_sources_of_service("xyz", "CPU load") == {}

    assert config_cache.labels_of_service("test-host", "CPU load") == {
        "label1": "val1",
        "label2": "val2",
    }
    assert config_cache.label_sources_of_service("test-host", "CPU load") == {
        "label1": "ruleset",
        "label2": "ruleset",
    }


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", None),
    ("testhost2", {
        "1": 1
    }),
])
def test_config_cache_rrd_config_of_service(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset("cmc_service_rrd_config", [
        ({
            "1": 1
        }, [], ["testhost2"], ["CPU load$"], {}),
        ({
            "2": 2
        }, [], ["testhost2"], ["CPU load$"], {}),
    ])
    config_cache = ts.apply(monkeypatch)
    assert config_cache.rrd_config_of_service(hostname, "CPU load") == result


def test_config_cache_get_host_config():
    cache = config.ConfigCache()
    assert cache._host_configs == {}

    host_config = cache.get_host_config("xyz")
    assert isinstance(host_config, config.HostConfig)
    assert host_config is cache.get_host_config("xyz")


def test_host_ruleset_match_object_of_host(monkeypatch):
    ts = Scenario()
    ts.set_option("host_tags", {
        "test-host": {
            "tag_group": "abc",
        },
    })
    ts.add_host("test-host", ["abc"])
    config_cache = ts.apply(monkeypatch)

    cfg = config_cache.get_host_config("xyz")
    assert isinstance(cfg.ruleset_match_object, RulesetMatchObject)
    assert cfg.ruleset_match_object.to_dict() == {
        "host_tags": {},
        "host_name": "xyz",
    }

    cfg = config_cache.get_host_config("test-host")
    assert isinstance(cfg.ruleset_match_object, RulesetMatchObject)
    assert cfg.ruleset_match_object.to_dict() == {
        "host_name": "test-host",
        "host_tags": {
            "tag_group": "abc",
        }
    }


def test_host_ruleset_match_object_of_service(monkeypatch):
    ts = Scenario()
    ts.set_option("host_tags", {
        "test-host": {
            "tag_group": "abc",
        },
    })
    ts.add_host("test-host", ["abc"])
    config_cache = ts.apply(monkeypatch)

    obj = config_cache.ruleset_match_object_of_service("xyz", "bla blä")
    assert isinstance(obj, RulesetMatchObject)
    assert obj.to_dict() == {
        "host_name": "xyz",
        "host_tags": {},
        "service_description": "bla blä",
    }

    obj = config_cache.ruleset_match_object_of_service("test-host", "CPU load")
    assert isinstance(obj, RulesetMatchObject)
    assert obj.to_dict() == {
        "host_name": "test-host",
        "host_tags": {
            "tag_group": "abc",
        },
        "service_description": "CPU load",
    }


@pytest.mark.parametrize("result,ruleset", [
    (False, None),
    (False, []),
    (False, [(None, [], config.ALL_HOSTS, {})]),
    (False, [({}, [], config.ALL_HOSTS, {})]),
    (True, [({
        "status_data_inventory": True
    }, [], config.ALL_HOSTS, {})]),
    (False, [({
        "status_data_inventory": False
    }, [], config.ALL_HOSTS, {})]),
])
def test_host_config_do_status_data_inventory(monkeypatch, result, ruleset):
    ts = Scenario().add_host("abc", [])
    ts.set_option("active_checks", {
        "cmk_inv": ruleset,
    })
    config_cache = ts.apply(monkeypatch)

    assert config_cache.get_host_config("abc").do_status_data_inventory == result


@pytest.mark.parametrize("result,ruleset", [
    (True, None),
    (True, []),
    (True, [(None, [], config.ALL_HOSTS, {})]),
    (True, [({}, [], config.ALL_HOSTS, {})]),
    (True, [({
        "host_label_inventory": True
    }, [], config.ALL_HOSTS, {})]),
    (False, [({
        "host_label_inventory": False
    }, [], config.ALL_HOSTS, {})]),
])
def test_host_config_do_host_label_discovery_for(monkeypatch, result, ruleset):
    ts = Scenario().add_host("abc", [])
    ts.set_option("active_checks", {
        "cmk_inv": ruleset,
    })
    config_cache = ts.apply(monkeypatch)

    assert config_cache.get_host_config("abc").do_host_label_discovery == result
