# encoding: utf-8
# pylint: disable=redefined-outer-name

from pathlib2 import Path
import pytest  # type: ignore
from testlib.base import Scenario

from cmk.utils.rulesets.ruleset_matcher import RulesetMatchObject
import cmk
import cmk.utils.paths
import cmk_base.config as config
import cmk_base.piggyback as piggyback
import cmk_base.check_api as check_api
from cmk_base.discovered_labels import DiscoveredServiceLabels


def test_duplicate_hosts(monkeypatch):
    ts = Scenario()
    ts.add_host("bla1")
    ts.add_host("bla1")
    ts.add_host("zzz")
    ts.add_host("zzz")
    ts.add_host("yyy")
    ts.apply(monkeypatch)
    assert config.duplicate_hosts() == ["bla1", "zzz"]


def test_all_offline_hosts(monkeypatch):
    ts = Scenario()
    ts.add_host("blub", tags={"criticality": "offline"})
    ts.add_host("bla")
    ts.apply(monkeypatch)
    assert config.all_offline_hosts() == set()


def test_all_offline_hosts_with_wato_default_config(monkeypatch):
    ts = Scenario(site_id="site1")
    ts.set_ruleset("only_hosts", [
        (["!offline"], config.ALL_HOSTS),
    ])
    ts.add_host("blub1", tags={"criticality": "offline"})
    ts.add_host("blub2", tags={"criticality": "offline", "site": "site2"})
    ts.add_host("bla")
    ts.apply(monkeypatch)
    assert config.all_offline_hosts() == {"blub1"}


def test_all_configured_offline_hosts(monkeypatch):
    ts = Scenario(site_id="site1")
    ts.set_ruleset("only_hosts", [
        (["!offline"], config.ALL_HOSTS),
    ])
    ts.add_host("blub1", tags={"criticality": "offline", "site": "site1"})
    ts.add_host("blub2", tags={"criticality": "offline", "site": "site2"})
    ts.apply(monkeypatch)
    assert config.all_offline_hosts() == {"blub1"}


def test_all_configured_hosts(monkeypatch):
    ts = Scenario(site_id="site1")
    ts.add_host("real1", tags={"site": "site1"})
    ts.add_host("real2", tags={"site": "site2"})
    ts.add_host("real3")
    ts.add_cluster("cluster1", tags={"site": "site1"}, nodes=["node1"])
    ts.add_cluster("cluster2", tags={"site": "site2"}, nodes=["node2"])
    ts.add_cluster("cluster3", nodes=["node3"])

    config_cache = ts.apply(monkeypatch)
    assert config_cache.all_configured_clusters() == {"cluster1", "cluster2", "cluster3"}
    assert config_cache.all_configured_realhosts() == {"real1", "real2", "real3"}
    assert config_cache.all_configured_hosts() == {
        "cluster1", "cluster2", "cluster3", "real1", "real2", "real3"
    }


def test_all_active_hosts(monkeypatch):
    ts = Scenario(site_id="site1")
    ts.add_host("real1", tags={"site": "site1"})
    ts.add_host("real2", tags={"site": "site2"})
    ts.add_host("real3")
    ts.add_cluster("cluster1", {"site": "site1"}, nodes=["node1"])
    ts.add_cluster("cluster2", {"site": "site2"}, nodes=["node2"])
    ts.add_cluster("cluster3", nodes=["node3"])

    config_cache = ts.apply(monkeypatch)
    assert config_cache.all_active_clusters() == {"cluster1", "cluster3"}
    assert config_cache.all_active_realhosts() == {"real1", "real3"}
    assert config_cache.all_active_hosts() == {"cluster1", "cluster3", "real1", "real3"}


def test_config_cache_tag_to_group_map(monkeypatch):
    ts = Scenario()
    ts.set_option(
        "tag_config", {
            "aux_tags": [],
            "tag_groups": [{
                'id': 'dingeling',
                'title': u'Dung',
                'tags': [{
                    'aux_tags': [],
                    'id': 'dong',
                    'title': u'ABC'
                },],
            }],
        })
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_tag_to_group_map() == {
        'all-agents': 'agent',
        'auto-piggyback': 'piggyback',
        'cmk-agent': 'agent',
        'dong': 'dingeling',
        'ip-v4': 'ip-v4',
        'ip-v4-only': 'address_family',
        'ip-v4v6': 'address_family',
        'ip-v6': 'ip-v6',
        'ip-v6-only': 'address_family',
        'no-agent': 'agent',
        'no-ip': 'address_family',
        'no-piggyback': 'piggyback',
        'no-snmp': 'snmp_ds',
        'piggyback': 'piggyback',
        'ping': 'ping',
        'snmp': 'snmp',
        'snmp-v1': 'snmp_ds',
        'snmp-v2': 'snmp_ds',
        'special-agents': 'agent',
        'tcp': 'tcp',
    }


@pytest.mark.parametrize("hostname,host_path,result", [
    ("none", "/hosts.mk", 0),
    ("main", "/wato/hosts.mk", 0),
    ("sub1", "/wato/level1/hosts.mk", 1),
    ("sub2", "/wato/level1/level2/hosts.mk", 2),
    ("sub3", "/wato/level1/level3/hosts.mk", 3),
    ("sub11", "/wato/level11/hosts.mk", 11),
    ("sub22", "/wato/level11/level22/hosts.mk", 22),
])
def test_host_folder_matching(monkeypatch, hostname, host_path, result):
    ts = Scenario().add_host(hostname, host_path=host_path)
    ts.set_ruleset("agent_ports", [
        (22, ["/wato/level11/level22/+"], config.ALL_HOSTS),
        (11, ["/wato/level11/+"], config.ALL_HOSTS),
        (3, ["/wato/level1/level3/+"], config.ALL_HOSTS),
        (2, ["/wato/level1/level2/+"], config.ALL_HOSTS),
        (1, ["/wato/level1/+"], config.ALL_HOSTS),
        (0, [], config.ALL_HOSTS),
    ])

    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).agent_port == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", {}, True),
    ("testhost", {
        "address_family": "ip-v4-only"
    }, True),
    ("testhost", {
        "address_family": "ip-v4v6"
    }, True),
    ("testhost", {
        "address_family": "ip-v6-only"
    }, False),
    ("testhost", {
        "address_family": "no-ip"
    }, False),
])
def test_is_ipv4_host(monkeypatch, hostname, tags, result):
    config_cache = Scenario().add_host(hostname, tags).apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_ipv4_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", {}, False),
    ("testhost", {
        "address_family": "ip-v4-only"
    }, False),
    ("testhost", {
        "address_family": "ip-v4v6"
    }, True),
    ("testhost", {
        "address_family": "ip-v6-only"
    }, True),
    ("testhost", {
        "address_family": "no-ip"
    }, False),
])
def test_is_ipv6_host(monkeypatch, hostname, tags, result):
    config_cache = Scenario().add_host(hostname, tags).apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_ipv6_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", {}, False),
    ("testhost", {
        "address_family": "ip-v4-only"
    }, False),
    ("testhost", {
        "address_family": "ip-v4v6"
    }, True),
    ("testhost", {
        "address_family": "ip-v6-only"
    }, False),
    ("testhost", {
        "address_family": "no-ip"
    }, False),
])
def test_is_ipv4v6_host(monkeypatch, hostname, tags, result):
    config_cache = Scenario().add_host(hostname, tags).apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_ipv4v6_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", {
        "piggyback": "piggyback"
    }, True),
    ("testhost", {
        "piggyback": "no-piggyback"
    }, False),
])
def test_is_piggyback_host(monkeypatch, hostname, tags, result):
    config_cache = Scenario().add_host(hostname, tags).apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_piggyback_host == result


@pytest.mark.parametrize("with_data,result", [
    (True, True),
    (False, False),
])
@pytest.mark.parametrize("hostname,tags", [
    ("testhost", {}),
    ("testhost", {
        "piggyback": "auto-piggyback"
    }),
])
def test_is_piggyback_host_auto(monkeypatch, hostname, tags, with_data, result):
    monkeypatch.setattr(piggyback, "has_piggyback_raw_data", lambda cache_age, hostname: with_data)
    config_cache = Scenario().add_host(hostname, tags).apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_piggyback_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", {}, False),
    ("testhost", {
        "address_family": "ip-v4-only"
    }, False),
    ("testhost", {
        "address_family": "ip-v4v6"
    }, False),
    ("testhost", {
        "address_family": "ip-v6-only"
    }, False),
    ("testhost", {
        "address_family": "no-ip"
    }, True),
])
def test_is_no_ip_host(monkeypatch, hostname, tags, result):
    config_cache = Scenario().add_host(hostname, tags).apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_no_ip_host == result


@pytest.mark.parametrize("hostname,tags,result,ruleset", [
    ("testhost", {}, False, []),
    ("testhost", {
        "address_family": "ip-v4-only"
    }, False, [
        ('ipv6', [], config.ALL_HOSTS, {}),
    ]),
    ("testhost", {
        "address_family": "ip-v4v6"
    }, False, []),
    ("testhost", {
        "address_family": "ip-v4v6"
    }, True, [
        ('ipv6', [], config.ALL_HOSTS, {}),
    ]),
    ("testhost", {
        "address_family": "ip-v6-only"
    }, True, []),
    ("testhost", {
        "address_family": "ip-v6-only"
    }, True, [
        ('ipv4', [], config.ALL_HOSTS, {}),
    ]),
    ("testhost", {
        "address_family": "ip-v6-only"
    }, True, [
        ('ipv6', [], config.ALL_HOSTS, {}),
    ]),
    ("testhost", {
        "address_family": "no-ip"
    }, False, []),
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
    ("testhost", {}, True),
    ("testhost", {
        "agent": "cmk-agent"
    }, True),
    ("testhost", {
        "agent": "cmk-agent",
        "snmp_ds": "snmp-v2"
    }, True),
    ("testhost", {
        "agent": "no-agent"
    }, False),
    ("testhost", {
        "agent": "no-agent",
        "snmp_ds": "no-snmp"
    }, False),
])
def test_is_tcp_host(monkeypatch, hostname, tags, result):
    config_cache = Scenario().add_host(hostname, tags).apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_tcp_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", {}, False),
    ("testhost", {
        "agent": "cmk-agent"
    }, False),
    ("testhost", {
        "agent": "cmk-agent",
        "snmp_ds": "snmp-v1"
    }, False),
    ("testhost", {
        "snmp_ds": "snmp-v1"
    }, False),
    ("testhost", {
        "agent": "no-agent",
        "snmp_ds": "no-snmp",
        "piggyback": "no-piggyback"
    }, True),
    ("testhost", {
        "agent": "no-agent",
        "snmp_ds": "no-snmp"
    }, True),
    ("testhost", {
        "agent": "no-agent"
    }, True),
])
def test_is_ping_host(monkeypatch, hostname, tags, result):
    config_cache = Scenario().add_host(hostname, tags).apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_ping_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", {}, False),
    ("testhost", {
        "agent": "cmk-agent"
    }, False),
    ("testhost", {
        "agent": "cmk-agent",
        "snmp_ds": "snmp-v1"
    }, True),
    ("testhost", {
        "agent": "cmk-agent",
        "snmp_ds": "snmp-v2"
    }, True),
    ("testhost", {
        "agent": "cmk-agent",
        "snmp_ds": "no-snmp"
    }, False),
])
def test_is_snmp_host(monkeypatch, hostname, tags, result):
    config_cache = Scenario().add_host(hostname, tags).apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_snmp_host == result


def test_is_not_usewalk_host(monkeypatch):
    config_cache = Scenario().add_host("xyz").apply(monkeypatch)
    assert config_cache.get_host_config("xyz").is_usewalk_host is False


def test_is_usewalk_host(monkeypatch):
    ts = Scenario()
    ts.add_host("xyz")
    ts.set_ruleset("usewalk_hosts", [
        (["xyz"], config.ALL_HOSTS, {}),
    ])

    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config("xyz").is_usewalk_host is False


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", {}, False),
    ("testhost", {
        "agent": "cmk-agent"
    }, False),
    ("testhost", {
        "agent": "no-agent",
        "snmp_ds": "snmp-v1"
    }, False),
    ("testhost", {
        "agent": "no-agent",
        "snmp_ds": "no-snmp"
    }, False),
    ("testhost", {
        "agent": "cmk-agent",
        "snmp_ds": "snmp-v1"
    }, True),
])
def test_is_dual_host(monkeypatch, hostname, tags, result):
    config_cache = Scenario().add_host(hostname, tags).apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_dual_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", {}, False),
    ("testhost", {
        "agent": "all-agents"
    }, True),
    ("testhost", {
        "agent": "special-agents"
    }, False),
    ("testhost", {
        "agent": "no-agent"
    }, False),
    ("testhost", {
        "agent": "cmk-agent"
    }, False),
])
def test_is_all_agents_host(monkeypatch, hostname, tags, result):
    config_cache = Scenario().add_host(hostname, tags).apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_all_agents_host == result


@pytest.mark.parametrize("hostname,tags,result", [
    ("testhost", {}, False),
    ("testhost", {
        "agent": "all-agents"
    }, False),
    ("testhost", {
        "agent": "special-agents"
    }, True),
    ("testhost", {
        "agent": "no-agent"
    }, False),
    ("testhost", {
        "agent": "cmk-agent"
    }, False),
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
    ("testhost2", ["abc", "dingdong"]),
])
def test_host_config_contactgroups(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset(
        "host_contactgroups",
        [
            # Seems both, a list of groups and a group name is allowed. We should clean
            # this up to be always a list of groups in the future...
            ("dingdong", [], ["testhost2"], {}),
            (["abc"], [], ["testhost2"], {}),
            (["xyz"], [], ["testhost2"], {}),
        ])
    config_cache = ts.apply(monkeypatch)
    assert sorted(config_cache.get_host_config(hostname).contactgroups) == sorted(result)


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
    ts = Scenario().add_host("test-host")
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


def test_config_cache_tag_list_of_host(monkeypatch):
    ts = Scenario()
    ts.add_host("test-host", tags={"agent": "no-agent"})
    ts.add_host("xyz")
    config_cache = ts.apply(monkeypatch)

    print config_cache._hosttags["test-host"]
    print config_cache._hosttags["xyz"]
    assert config_cache.tag_list_of_host("xyz") == {
        '/wato/', 'lan', 'ip-v4', 'cmk-agent', 'no-snmp', 'tcp', 'auto-piggyback', 'ip-v4-only',
        'site:unit', 'prod'
    }


def test_config_cache_tag_list_of_host_not_existing(monkeypatch):
    ts = Scenario()
    config_cache = ts.apply(monkeypatch)

    assert config_cache.tag_list_of_host("not-existing") == {
        '/', 'lan', 'cmk-agent', 'no-snmp', 'auto-piggyback', 'ip-v4-only', 'site:NO_SITE', 'prod'
    }


def test_host_tags_default():
    assert isinstance(config.host_tags, dict)


def test_host_tags_of_host(monkeypatch):
    ts = Scenario()
    ts.add_host("test-host", tags={"agent": "no-agent"})
    ts.add_host("xyz")
    config_cache = ts.apply(monkeypatch)

    cfg = config_cache.get_host_config("xyz")
    assert cfg.tag_groups == {
        'address_family': 'ip-v4-only',
        'agent': 'cmk-agent',
        'criticality': 'prod',
        'ip-v4': 'ip-v4',
        'networking': 'lan',
        'piggyback': 'auto-piggyback',
        'site': 'unit',
        'snmp_ds': 'no-snmp',
        'tcp': 'tcp',
    }
    assert config_cache.tags_of_host("xyz") == cfg.tag_groups

    cfg = config_cache.get_host_config("test-host")
    assert cfg.tag_groups == {
        'address_family': 'ip-v4-only',
        'agent': 'no-agent',
        'criticality': 'prod',
        'ip-v4': 'ip-v4',
        'networking': 'lan',
        'piggyback': 'auto-piggyback',
        'site': 'unit',
        'snmp_ds': 'no-snmp',
    }
    assert config_cache.tags_of_host("test-host") == cfg.tag_groups


def test_service_tag_rules_default():
    assert isinstance(config.service_tag_rules, list)


def test_tags_of_service(monkeypatch):
    ts = Scenario()
    ts.set_ruleset("service_tag_rules", [
        ([("criticality", "prod")], ["no-agent"], config.ALL_HOSTS, ["CPU load$"], {}),
    ])

    ts.add_host("test-host", tags={"agent": "no-agent"})
    ts.add_host("xyz")
    config_cache = ts.apply(monkeypatch)

    cfg = config_cache.get_host_config("xyz")
    assert cfg.tag_groups == {
        'address_family': 'ip-v4-only',
        'agent': 'cmk-agent',
        'criticality': 'prod',
        'ip-v4': 'ip-v4',
        'networking': 'lan',
        'piggyback': 'auto-piggyback',
        'site': 'unit',
        'snmp_ds': 'no-snmp',
        'tcp': 'tcp',
    }
    assert config_cache.tags_of_service("xyz", "CPU load") == {}

    cfg = config_cache.get_host_config("test-host")
    assert cfg.tag_groups == {
        'address_family': 'ip-v4-only',
        'agent': 'no-agent',
        'criticality': 'prod',
        'ip-v4': 'ip-v4',
        'networking': 'lan',
        'piggyback': 'auto-piggyback',
        'site': 'unit',
        'snmp_ds': 'no-snmp',
    }
    assert config_cache.tags_of_service("test-host", "CPU load") == {"criticality": "prod"}


def test_host_label_rules_default():
    assert isinstance(config.host_label_rules, list)


def test_host_config_labels(monkeypatch):
    ts = Scenario()
    ts.set_ruleset("host_label_rules", [
        ({
            "from-rule": "rule1"
        }, ["no-agent"], config.ALL_HOSTS, {}),
        ({
            "from-rule2": "rule2"
        }, ["no-agent"], config.ALL_HOSTS, {}),
    ])

    ts.add_host("test-host", tags={"agent": "no-agent"}, labels={"explicit": "ding"})
    ts.add_host("xyz")
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
    ts = Scenario().add_host("test-host")

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
        }, ["no-agent"], config.ALL_HOSTS, ["CPU load$"], {}),
        ({
            "label2": "val2"
        }, ["no-agent"], config.ALL_HOSTS, ["CPU load$"], {}),
    ])

    ts.add_host("test-host", tags={"agent": "no-agent"})
    config_cache = ts.apply(monkeypatch)

    assert config_cache.labels_of_service("xyz", "CPU load", DiscoveredServiceLabels()) == {}
    assert config_cache.label_sources_of_service("xyz", "CPU load", DiscoveredServiceLabels()) == {}

    assert config_cache.labels_of_service("test-host", "CPU load", DiscoveredServiceLabels()) == {
        "label1": "val1",
        "label2": "val2",
    }
    assert config_cache.label_sources_of_service("test-host", "CPU load",
                                                 DiscoveredServiceLabels()) == {
                                                     "label1": "ruleset",
                                                     "label2": "ruleset",
                                                 }


def test_labels_of_service_discovered_labels(monkeypatch, tmp_path):
    config.load_checks(check_api.get_check_api_context, ["checks/cpu"])

    ts = Scenario().add_host("test-host")

    monkeypatch.setattr(cmk.utils.paths, "autochecks_dir", str(tmp_path))
    autochecks_file = Path(cmk.utils.paths.autochecks_dir).joinpath("test-host.mk")
    with autochecks_file.open("w", encoding="utf-8") as f:  # pylint: disable=no-member
        f.write(u"""[
    {'check_plugin_name': 'cpu.loads', 'item': None, 'parameters': cpuload_default_levels, 'service_labels': {u'äzzzz': u'eeeeez'}},
]""")

    config_cache = ts.apply(monkeypatch)

    service = config_cache.get_autochecks_of("test-host")[0]
    assert service.description == u"CPU load"

    assert config_cache.labels_of_service("xyz", u"CPU load", DiscoveredServiceLabels()) == {}
    assert config_cache.label_sources_of_service("xyz", u"CPU load",
                                                 DiscoveredServiceLabels()) == {}

    assert config_cache.labels_of_service("test-host", service.description,
                                          service.service_labels) == {
                                              u"äzzzz": u"eeeeez"
                                          }
    assert config_cache.label_sources_of_service("test-host", service.description,
                                                 service.service_labels) == {
                                                     u"äzzzz": u"discovered"
                                                 }


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", {
        "check_interval": 1.0
    }),
    ("testhost2", {
        '_CUSTOM': ['value1'],
        'dingdong': ['value1'],
        'check_interval': 10.0,
    }),
])
def test_config_cache_extra_attributes_of_service(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_option(
        "extra_service_conf", {
            "check_interval": [("10", [], ["testhost2"], "CPU load$", {}),],
            "dingdong": [
                ([
                    "value1",
                ], [], ["testhost2"], "CPU load$", {}),
                ([
                    "value2",
                ], [], ["testhost2"], "CPU load$", {}),
            ],
            "_custom": [
                ([
                    "value1",
                ], [], ["testhost2"], "CPU load$", {}),
                ([
                    "value2",
                ], [], ["testhost2"], "CPU load$", {}),
            ],
        })
    config_cache = ts.apply(monkeypatch)
    assert config_cache.extra_attributes_of_service(hostname, "CPU load") == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", []),
    ("testhost2", ["icon1", "icon2"]),
])
def test_config_cache_icons_and_actions(monkeypatch, hostname, result):
    config.load_checks(check_api.get_check_api_context, ["checks/ps"])
    ts = Scenario().add_host(hostname)
    ts.set_ruleset("service_icons_and_actions", [
        ("icon1", [], ["testhost2"], "CPU load$", {}),
        ("icon1", [], ["testhost2"], "CPU load$", {}),
        ("icon2", [], ["testhost2"], "CPU load$", {}),
    ])
    config_cache = ts.apply(monkeypatch)
    assert sorted(config_cache.icons_and_actions_of_service(hostname, "CPU load", "ps",
                                                            {})) == sorted(result)


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", []),
    ("testhost2", ["dingdong"]),
])
def test_config_cache_servicegroups_of_service(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset("service_groups", [
        ("dingdong", [], ["testhost2"], "CPU load$", {}),
    ])
    config_cache = ts.apply(monkeypatch)
    assert config_cache.servicegroups_of_service(hostname, "CPU load") == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", []),
    ("testhost2", ["dingdong"]),
])
def test_config_cache_contactgroups_of_service(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset("service_contactgroups", [
        ("dingdong", [], ["testhost2"], "CPU load", {}),
    ])
    config_cache = ts.apply(monkeypatch)
    assert config_cache.contactgroups_of_service(hostname, "CPU load") == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", "24X7"),
    ("testhost2", "workhours"),
])
def test_config_cache_passive_check_period_of_service(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset("check_periods", [
        ("workhours", [], ["testhost2"], ["CPU load$"], {}),
    ])
    config_cache = ts.apply(monkeypatch)
    assert config_cache.passive_check_period_of_service(hostname, "CPU load") == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", {}),
    ("testhost2", {
        'ATTR1': 'value1',
        'ATTR2': 'value2',
    }),
])
def test_config_cache_custom_attributes_of_service(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset(
        "custom_service_attributes",
        [
            ([
                ("ATTR1", "value1"),
                ("ATTR2", "value2"),
            ], [], ["testhost2"], ["CPU load$"], {}),
            ([
                ("ATTR1", "value1"),
            ], [], ["testhost2"], ["CPU load$"], {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.custom_attributes_of_service(hostname, "CPU load") == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", None),
    ("testhost2", 10),
])
def test_config_cache_service_level_of_service(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset(
        "service_service_levels",
        [
            (10, [], ["testhost2"], ["CPU load$"], {}),
            (2, [], ["testhost2"], ["CPU load$"], {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.service_level_of_service(hostname, "CPU load") == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", None),
    ("testhost2", None),
    ("testhost3", "xyz"),
])
def test_config_cache_check_period_of_service(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset(
        "check_periods",
        [
            ("24X7", [], ["testhost2"], ["CPU load$"], {}),
            ("xyz", [], ["testhost3"], ["CPU load$"], {}),
            ("zzz", [], ["testhost3"], ["CPU load$"], {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.check_period_of_service(hostname, "CPU load") == result


@pytest.mark.parametrize("edition_short,expected_cache_class_name,expected_host_class_name", [
    ("cme", "CEEConfigCache", "CEEHostConfig"),
    ("cee", "CEEConfigCache", "CEEHostConfig"),
    ("cre", "ConfigCache", "HostConfig"),
])
def test_config_cache_get_host_config(monkeypatch, edition_short, expected_cache_class_name,
                                      expected_host_class_name):
    monkeypatch.setattr(cmk, "edition_short", lambda: edition_short)

    ts = Scenario()
    ts.add_host("xyz")
    cache = ts.apply(monkeypatch)

    assert cache.__class__.__name__ == expected_cache_class_name
    assert cache._host_configs.keys() == ["xyz"]

    host_config = cache.get_host_config("xyz")
    assert host_config.__class__.__name__ == expected_host_class_name
    assert isinstance(host_config, config.HostConfig)
    assert host_config is cache.get_host_config("xyz")


def test_config_cache_ruleset_match_object_of_host(monkeypatch):
    ts = Scenario()
    ts.add_host("test-host", tags={"agent": "no-agent"})
    ts.add_host("xyz")
    config_cache = ts.apply(monkeypatch)

    ruleset_match_object = config_cache.ruleset_match_object_of_host("xyz")
    assert isinstance(ruleset_match_object, RulesetMatchObject)
    assert ruleset_match_object.to_dict() == {
        "host_folder": '/wato/',
        "host_tags": {
            'address_family': 'ip-v4-only',
            'agent': 'cmk-agent',
            'criticality': 'prod',
            'ip-v4': 'ip-v4',
            'networking': 'lan',
            'piggyback': 'auto-piggyback',
            'site': 'unit',
            'snmp_ds': 'no-snmp',
            'tcp': 'tcp',
        },
        "host_name": "xyz",
    }

    ruleset_match_object = config_cache.ruleset_match_object_of_host("test-host")
    assert isinstance(ruleset_match_object, RulesetMatchObject)
    assert ruleset_match_object.to_dict() == {
        "host_folder": '/wato/',
        "host_name": "test-host",
        "host_tags": {
            'address_family': 'ip-v4-only',
            'agent': 'no-agent',
            'criticality': 'prod',
            'ip-v4': 'ip-v4',
            'networking': 'lan',
            'piggyback': 'auto-piggyback',
            'site': 'unit',
            'snmp_ds': 'no-snmp',
        }
    }


def test_host_ruleset_match_object_of_service(monkeypatch):
    ts = Scenario()
    ts.add_host("test-host", tags={"agent": "no-agent"})
    ts.add_host("xyz")
    config_cache = ts.apply(monkeypatch)

    obj = config_cache.ruleset_match_object_of_service("xyz", "bla blä")
    assert isinstance(obj, RulesetMatchObject)
    assert obj.to_dict() == {
        "host_folder": '/wato/',
        "host_name": "xyz",
        "host_tags": {
            'address_family': 'ip-v4-only',
            'agent': 'cmk-agent',
            'criticality': 'prod',
            'ip-v4': 'ip-v4',
            'networking': 'lan',
            'piggyback': 'auto-piggyback',
            'site': 'unit',
            'snmp_ds': 'no-snmp',
            'tcp': 'tcp',
        },
        "service_description": "bla blä",
    }

    obj = config_cache.ruleset_match_object_of_service("test-host", "CPU load")
    assert isinstance(obj, RulesetMatchObject)
    assert obj.to_dict() == {
        "host_folder": '/wato/',
        "host_name": "test-host",
        "host_tags": {
            'address_family': 'ip-v4-only',
            'agent': 'no-agent',
            'criticality': 'prod',
            'ip-v4': 'ip-v4',
            'networking': 'lan',
            'piggyback': 'auto-piggyback',
            'site': 'unit',
            'snmp_ds': 'no-snmp',
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
    ts = Scenario().add_host("abc")
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
    ts = Scenario().add_host("abc")
    ts.set_option("active_checks", {
        "cmk_inv": ruleset,
    })
    config_cache = ts.apply(monkeypatch)

    assert config_cache.get_host_config("abc").do_host_label_discovery == result


@pytest.mark.parametrize("hostname,result", [
    ("testhost1", None),
    ("testhost2", 10),
])
def test_host_config_service_level(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset(
        "host_service_levels",
        [
            (10, [], ["testhost2"], {}),
            (2, [], ["testhost2"], {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).service_level == result
