#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest  # type: ignore[import]
from six import ensure_str

# No stub file
from testlib.base import Scenario  # type: ignore[import]

import cmk.utils.paths
import cmk.utils.piggyback as piggyback
import cmk.utils.version as cmk_version
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.rulesets.ruleset_matcher import RulesetMatchObject
from cmk.utils.type_defs import (
    CheckPluginName,
    ConfigSerial,
    HostKey,
    LATEST_SERIAL,
    SectionName,
    SourceType,
)

from cmk.fetchers.type_defs import Mode

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.config as config
from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.type_defs import ParsedSectionName, SNMPSectionPlugin
from cmk.base.caching import config_cache as _config_cache
from cmk.base.check_utils import Service
from cmk.base.discovered_labels import DiscoveredServiceLabels, ServiceLabel


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
    monkeypatch.setattr(piggyback, "has_piggyback_raw_data", lambda hostname, cache_age: with_data)
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


def _management_config_ruleset():
    return [
        {
            'condition': {},
            'value': ('snmp', 'eee')
        },
        {
            'condition': {},
            'value': ('ipmi', {
                'username': 'eee',
                'password': 'eee'
            })
        },
    ]


@pytest.mark.parametrize("expected_result,protocol,credentials,ruleset", [
    (None, None, None, []),
    ("public", "snmp", None, []),
    (None, "ipmi", None, []),
    ("aaa", "snmp", "aaa", []),
    ({
        'username': 'aaa',
        'password': 'aaa'
    }, "ipmi", {
        'username': 'aaa',
        'password': 'aaa'
    }, []),
    (None, None, None, _management_config_ruleset()),
    ("eee", "snmp", None, _management_config_ruleset()),
    ({
        'username': 'eee',
        'password': 'eee'
    }, "ipmi", None, _management_config_ruleset()),
    ("aaa", "snmp", "aaa", _management_config_ruleset()),
    ({
        'username': 'aaa',
        'password': 'aaa'
    }, "ipmi", {
        'username': 'aaa',
        'password': 'aaa'
    }, _management_config_ruleset()),
])
def test_host_config_management_credentials(monkeypatch, protocol, credentials, expected_result,
                                            ruleset):
    ts = Scenario().add_host("hostname")
    ts.set_option("host_attributes", {"hostname": {"management_address": "127.0.0.1"}})
    ts.set_option("management_protocol", {"hostname": protocol})

    if credentials is not None:
        if protocol == "snmp":
            ts.set_option("management_snmp_credentials", {"hostname": credentials})
        elif protocol == "ipmi":
            ts.set_option("management_ipmi_credentials", {"hostname": credentials})
        else:
            raise NotImplementedError()

    ts.set_ruleset("management_board_config", ruleset)
    config_cache = ts.apply(monkeypatch)
    host_config = config_cache.get_host_config("hostname")

    assert host_config.management_credentials == expected_result

    # Test management_snmp_config on the way...
    if protocol == "snmp":
        assert host_config.management_snmp_config.credentials == expected_result


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
    ("testhost2", cmk_version.__version__),
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


@pytest.mark.parametrize(
    "hostname,result",
    [
        # No rule matches for this host
        ("testhost1", []),
        # Take the group from the ruleset (dingdong) and the definition from the nearest folder in
        # the hierarchy (abc). Don't apply the definition from the parent folder (xyz).
        ("testhost2", ["abc", "dingdong"]),
        # Take the group from all rulesets (dingdong, haha) and the definition from the nearest
        # folder in the hierarchy (abc). Don't apply the definition from the parent folder (xyz).
        ("testhost3", ["abc", "dingdong", "haha"]),
    ])
def test_host_config_contactgroups(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset(
        "host_contactgroups",
        [
            # Seems both, a list of groups and a group name is allowed. We should clean
            # this up to be always a list of groups in the future...
            ("dingdong", [], ["testhost2", "testhost3"], {}),
            (["abc"], [], ["testhost2", "testhost3"], {}),
            (["xyz"], [], ["testhost2", "testhost3"], {}),
            ("haha", [], ["testhost3"], {}),
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


@pytest.mark.parametrize("ruleset", [
    {
        "empty_output": 2,
        'restricted_address_mismatch': 2,
    },
    {
        "overall": {
            "empty_output": 2,
        },
        'restricted_address_mismatch': 2,
    },
    {
        "individual": {
            "snmp": {
                "empty_output": 2,
            }
        },
        'restricted_address_mismatch': 2,
    },
    {
        "overall": {
            "empty_output": 1000,
        },
        "individual": {
            "snmp": {
                "empty_output": 2,
            }
        },
        'restricted_address_mismatch': 2,
    },
])
def test_host_config_exit_code_spec(monkeypatch, ruleset):
    hostname = "hostname"
    ts = Scenario().add_host(hostname)
    ts.set_ruleset("check_mk_exit_status", [
        (ruleset, [], ["hostname"], {}),
    ])
    config_cache = ts.apply(monkeypatch)
    host_config = config_cache.get_host_config(hostname)

    exit_code_spec = host_config.exit_code_spec()
    assert 'restricted_address_mismatch' in exit_code_spec
    assert exit_code_spec['restricted_address_mismatch'] == 2

    result = {
        "empty_output": 2,
        'restricted_address_mismatch': 2,
    }
    snmp_exit_code_spec = host_config.exit_code_spec(data_source_id="snmp")
    assert snmp_exit_code_spec == result


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


@pytest.mark.usefixtures("config_load_all_checks")
@pytest.mark.parametrize("hostname,section_name,result", [
    ("testhost1", "uptime", None),
    ("testhost2", "uptime", None),
    ("testhost1", "snmp_uptime", None),
    ("testhost2", "snmp_uptime", 4),
])
def test_host_config_snmp_check_interval(monkeypatch, hostname, section_name, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset("snmp_check_interval", [
        (("snmp_uptime", 4), [], ["testhost2"], {}),
    ])
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).snmp_fetch_interval(
        SectionName(section_name)) == result


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


@pytest.fixture(name="cluster_config")
def cluster_config_fixture(monkeypatch):
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

    print(config_cache._hosttags["test-host"])
    print(config_cache._hosttags["xyz"])
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
    with host_file.open(mode="w", encoding="utf-8") as f:
        f.write(ensure_str(repr({u"äzzzz": {"value": u"eeeeez", "plugin_name": "ding123"}}) + "\n"))

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


@pytest.mark.usefixtures("config_load_all_checks")
def test_labels_of_service_discovered_labels(monkeypatch, tmp_path):
    ts = Scenario().add_host("test-host")

    monkeypatch.setattr(cmk.utils.paths, "autochecks_dir", str(tmp_path))
    autochecks_file = Path(cmk.utils.paths.autochecks_dir, "test-host.mk")
    with autochecks_file.open("w", encoding="utf-8") as f:
        f.write(u"""[
    {'check_plugin_name': 'cpu_loads', 'item': None, 'parameters': (5.0, 10.0), 'service_labels': {u'äzzzz': u'eeeeez'}},
]""")

    config_cache = ts.apply(monkeypatch)

    service = config_cache.get_autochecks_of("test-host")[0]
    assert service.description == u"CPU load"

    assert config_cache.labels_of_service("xyz", u"CPU load") == {}
    assert config_cache.label_sources_of_service("xyz", u"CPU load") == {}

    assert config_cache.labels_of_service("test-host", service.description) == {u"äzzzz": u"eeeeez"}
    assert config_cache.label_sources_of_service("test-host", service.description) == {
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


@pytest.mark.usefixtures("config_load_all_checks")
@pytest.mark.parametrize("hostname,result", [
    ("testhost1", []),
    ("testhost2", ["icon1", "icon2"]),
])
def test_config_cache_icons_and_actions(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset("service_icons_and_actions", [
        ("icon1", [], ["testhost2"], "CPU load$", {}),
        ("icon1", [], ["testhost2"], "CPU load$", {}),
        ("icon2", [], ["testhost2"], "CPU load$", {}),
    ])
    config_cache = ts.apply(monkeypatch)
    assert sorted(
        config_cache.icons_and_actions_of_service(hostname, "CPU load", CheckPluginName("ps"),
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


@pytest.mark.parametrize(
    "hostname,result",
    [
        # No rule matches for this host
        ("testhost1", []),
        # Take the group from the ruleset (dingdong) and the definition from the nearest folder in
        # the hierarchy (abc). Don't apply the definition from the parent folder (xyz).
        ("testhost2", ["abc", "dingdong"]),
        # Take the group from all rulesets (dingdong, haha) and the definition from the nearest
        # folder in the hierarchy (abc). Don't apply the definition from the parent folder (xyz).
        ("testhost3", ["abc", "dingdong", "haha"]),
    ])
def test_config_cache_contactgroups_of_service(monkeypatch, hostname, result):
    ts = Scenario().add_host(hostname)
    ts.set_ruleset(
        "service_contactgroups",
        [
            # Just like host_contactgroups, a list of groups and a group name is
            # allowed. We should clean this up to be always a list of groups in the
            # future...
            ("dingdong", [], ["testhost2", "testhost3"], "CPU load", {}),
            (["abc"], [], ["testhost2", "testhost3"], "CPU load", {}),
            (["xyz"], [], ["testhost2", "testhost3"], "CPU load", {}),
            ("haha", [], ["testhost3"], "CPU load", {}),
        ])
    config_cache = ts.apply(monkeypatch)
    assert sorted(config_cache.contactgroups_of_service(hostname, "CPU load")) == sorted(result)


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
    monkeypatch.setattr(cmk_version, "edition_short", lambda: edition_short)

    _config_cache.reset()

    ts = Scenario()
    ts.add_host("xyz")
    cache = ts.apply(monkeypatch)

    assert cache.__class__.__name__ == expected_cache_class_name

    host_config = cache.get_host_config("xyz")
    assert host_config.__class__.__name__ == expected_host_class_name
    assert isinstance(host_config, config.HostConfig)
    assert host_config is cache.get_host_config("xyz")


def test_host_config_max_cachefile_age_no_cluster(monkeypatch):
    ts = Scenario()
    ts.add_host("xyz")
    ts.apply(monkeypatch)

    host_config = config.HostConfig.make_host_config("xyz")
    assert not host_config.is_cluster
    assert host_config.max_cachefile_age.get(Mode.CHECKING) == config.check_max_cachefile_age
    assert host_config.max_cachefile_age.get(Mode.CHECKING) != config.cluster_max_cachefile_age


def test_host_config_max_cachefile_age_cluster(monkeypatch):
    ts = Scenario()
    ts.add_cluster("clu")
    ts.apply(monkeypatch)

    host_config = config.HostConfig.make_host_config("clu")
    assert host_config.is_cluster
    assert host_config.max_cachefile_age.get(Mode.CHECKING) != config.check_max_cachefile_age
    assert host_config.max_cachefile_age.get(Mode.CHECKING) == config.cluster_max_cachefile_age


@pytest.mark.parametrize("use_new_descr,result", [
    (True, "Check_MK Discovery"),
    (False, "Check_MK inventory"),
])
def test_config_cache_service_discovery_name(monkeypatch, use_new_descr, result):
    ts = Scenario()
    if use_new_descr:
        ts.set_option("use_new_descriptions_for", ["cmk_inventory"])
    config_cache = ts.apply(monkeypatch)

    assert config_cache.service_discovery_name() == result


def test_config_cache_get_clustered_service_node_keys_no_cluster(monkeypatch):
    ts = Scenario()

    config_cache = ts.apply(monkeypatch)

    # regardless of config: descr == None -> return None
    assert config_cache.get_clustered_service_node_keys(
        'cluster.test',
        SourceType.HOST,
        None,
        lambda _x: "dummy.test.ip.0",
    ) is None
    # still None, we have no cluster:
    assert config_cache.get_clustered_service_node_keys(
        'cluster.test',
        SourceType.HOST,
        'Test Service',
        lambda _x: "dummy.test.ip.0",
    ) is None


def test_config_cache_get_clustered_service_node_keys_cluster_no_service(monkeypatch):
    ts = Scenario()
    ts.add_cluster('cluster.test', nodes=['node1.test', 'node2.test'])
    config_cache = ts.apply(monkeypatch)

    # None for a node:
    assert config_cache.get_clustered_service_node_keys(
        'node1.test',
        SourceType.HOST,
        'Test Service',
        lambda _x: "dummy.test.ip.0",
    ) is None
    # all nodes for cluster (we have not clustered the service -> use all nodes)
    assert config_cache.get_clustered_service_node_keys(
        'cluster.test',
        SourceType.HOST,
        'Test Service',
        lambda _x: "dummy.test.ip.0",
    ) == [
        HostKey(hostname='node1.test', ipaddress='dummy.test.ip.0', source_type=SourceType.HOST),
        HostKey(hostname='node2.test', ipaddress='dummy.test.ip.0', source_type=SourceType.HOST),
    ]


def test_config_cache_get_clustered_service_node_keys_clustered(monkeypatch):
    ts = Scenario()
    ts.add_host('node1.test')
    ts.add_host('node2.test')
    ts.add_cluster('cluster.test', nodes=['node1.test', 'node2.test'])
    # add a fake rule, that defines a cluster
    ts.set_option('clustered_services_mapping', [{
        'value': 'cluster.test',
        'condition': {
            'service_description': ['Test Service']
        },
    }])
    config_cache = ts.apply(monkeypatch)

    assert config_cache.get_clustered_service_node_keys(
        'cluster.test',
        SourceType.HOST,
        'Test Service',
        lambda host_config: "dummy.test.ip.%s" % host_config.hostname[4],
    ) == [
        HostKey('node1.test', "dummy.test.ip.1", SourceType.HOST),
        HostKey('node2.test', "dummy.test.ip.2", SourceType.HOST),
    ]
    assert config_cache.get_clustered_service_node_keys(
        'cluster.test',
        SourceType.HOST,
        'Test Unclustered',
        lambda _x: "dummy.test.ip.0",
    ) == [
        HostKey(hostname='node1.test', ipaddress='dummy.test.ip.0', source_type=SourceType.HOST),
        HostKey(hostname='node2.test', ipaddress='dummy.test.ip.0', source_type=SourceType.HOST),
    ]
    # regardless of config: descr == None -> return None
    assert config_cache.get_clustered_service_node_keys(
        'cluster.test',
        SourceType.HOST,
        None,
        lambda _x: "dummy.test.ip.0",
    ) is None


def test_host_ruleset_match_object_of_service(monkeypatch):
    ts = Scenario()
    ts.add_host("xyz")
    ts.add_host("test-host", tags={"agent": "no-agent"})
    ts.set_autochecks("test-host", [
        Service(
            CheckPluginName("cpu_load"),
            None,
            "CPU load",
            "{}",
            service_labels=DiscoveredServiceLabels(ServiceLabel(u"abc", u"xä"),),
        )
    ])
    config_cache = ts.apply(monkeypatch)

    obj = config_cache.ruleset_match_object_of_service("xyz", u"bla blä")
    assert isinstance(obj, RulesetMatchObject)
    assert obj.to_dict() == {
        "host_name": "xyz",
        "service_description": u"bla blä",
        "service_labels": {},
        "service_cache_id": (u'bla blä', hash(frozenset([]))),
    }

    obj = config_cache.ruleset_match_object_of_service("test-host", "CPU load")
    service_labels = {u"abc": u"xä"}
    assert isinstance(obj, RulesetMatchObject)
    assert obj.to_dict() == {
        "host_name": "test-host",
        "service_description": "CPU load",
        "service_labels": service_labels,
        "service_cache_id": ('CPU load', hash(frozenset(service_labels.items()))),
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


@pytest.mark.parametrize("params,ignored,ping,result", [
    (None, False, False, False),
    ({
        "check_interval": 0
    }, False, False, False),
    ({
        "check_interval": 3600
    }, False, False, True),
    ({
        "check_interval": 3600
    }, True, False, False),
    ({
        "check_interval": 3600
    }, False, True, False),
])
def test_host_config_add_discovery_check(monkeypatch, params, ignored, ping, result):
    if ping:
        tags = {
            "agent": "no-agent",
            "snmp_ds": "no-snmp",
            "piggyback": "no-piggyback",
        }
    else:
        tags = {}

    ts = Scenario().add_host("xyz", tags=tags)

    if ignored:
        ts.set_ruleset(
            "ignored_services",
            [
                {
                    'condition': {
                        'service_description': [{
                            '$regex': u'Check_MK Discovery'
                        }],
                        'host_name': ['xyz'],
                    },
                    'value': True
                },
            ],
        )
    config_cache = ts.apply(monkeypatch)

    host_config = config_cache.get_host_config("xyz")
    assert host_config.add_service_discovery_check(params, "Check_MK Discovery") == result


def test_get_config_file_paths_with_confd(folder_path_test_config):
    rel_paths = [
        "%s" % p.relative_to(cmk.utils.paths.default_config_dir)
        for p in config._get_config_file_paths(with_conf_d=True)
    ]
    assert rel_paths == [
        'main.mk',
        'conf.d/wato/hosts.mk',
        'conf.d/wato/rules.mk',
        'conf.d/wato/lvl1/hosts.mk',
        'conf.d/wato/lvl1/rules.mk',
        'conf.d/wato/lvl1/lvl2/hosts.mk',
        'conf.d/wato/lvl1/lvl2/rules.mk',
        'conf.d/wato/lvl1_aaa/hosts.mk',
        'conf.d/wato/lvl1_aaa/rules.mk',
    ]


def test_load_config_folder_paths(folder_path_test_config):
    assert config.host_paths == {
        'lvl1-host': '/wato/lvl1/hosts.mk',
        'lvl1aaa-host': '/wato/lvl1_aaa/hosts.mk',
        'lvl2-host': '/wato/lvl1/lvl2/hosts.mk',
        'lvl0-host': '/wato/hosts.mk',
    }

    config_cache = config.get_config_cache()

    assert config_cache.host_path("main-host") == "/"
    assert config_cache.host_path("lvl0-host") == "/wato/"
    assert config_cache.host_path("lvl1-host") == "/wato/lvl1/"
    assert config_cache.host_path("lvl1aaa-host") == "/wato/lvl1_aaa/"
    assert config_cache.host_path("lvl2-host") == "/wato/lvl1/lvl2/"

    assert config.cmc_host_rrd_config[0]["condition"]["host_folder"] == "/wato/lvl1_aaa/"
    assert config.cmc_host_rrd_config[1]["condition"]["host_folder"] == "/wato/lvl1/lvl2/"
    assert config.cmc_host_rrd_config[2]["condition"]["host_folder"] == "/wato/lvl1/"
    assert "host_folder" not in config.cmc_host_rrd_config[3]["condition"]
    assert "host_folder" not in config.cmc_host_rrd_config[4]["condition"]

    assert config_cache.host_extra_conf("main-host", config.cmc_host_rrd_config) == ["LVL0", "MAIN"]
    assert config_cache.host_extra_conf("lvl0-host", config.cmc_host_rrd_config) == ["LVL0", "MAIN"]
    assert config_cache.host_extra_conf("lvl1-host",
                                        config.cmc_host_rrd_config) == ["LVL1", "LVL0", "MAIN"]
    assert config_cache.host_extra_conf("lvl1aaa-host",
                                        config.cmc_host_rrd_config) == ["LVL1aaa", "LVL0", "MAIN"]
    assert config_cache.host_extra_conf(
        "lvl2-host", config.cmc_host_rrd_config) == ["LVL2", "LVL1", "LVL0", "MAIN"]


@pytest.fixture(name="folder_path_test_config")
def folder_path_test_config_fixture(monkeypatch):
    config_dir = Path(cmk.utils.paths.check_mk_config_dir)
    config_dir.mkdir(parents=True, exist_ok=True)

    with Path(cmk.utils.paths.main_config_file).open("w", encoding="utf-8") as f:
        f.write(u"""
all_hosts += ['%(name)s']

host_tags.update({'%(name)s': {}})

ipaddresses.update({'%(name)s': '127.0.0.1'})

host_tags.update({
    '%(name)s': {
        'piggyback': 'auto-piggyback',
        'networking': 'lan',
        'agent': 'cmk-agent',
        'criticality': 'prod',
        'snmp_ds': 'no-snmp',
        'ip-v4': 'ip-v4',
        'ip-v6': 'ip-v6',
        'site': 'unit',
        'tcp': 'tcp',
        'address_family': 'ip-v4v6',
    }
})

cmc_host_rrd_config = [
{'condition': {}, 'value': 'MAIN'},
] + cmc_host_rrd_config

""" % {"name": "main-host"})

    wato_main_folder = config_dir / "wato"
    wato_main_folder.mkdir(parents=True, exist_ok=True)
    _add_host_in_folder(wato_main_folder, "lvl0-host")
    _add_rule_in_folder(wato_main_folder, "LVL0")

    wato_lvl1_folder = wato_main_folder / "lvl1"
    wato_lvl1_folder.mkdir(parents=True, exist_ok=True)
    _add_host_in_folder(wato_lvl1_folder, "lvl1-host")
    _add_rule_in_folder(wato_lvl1_folder, "LVL1")

    wato_lvl1a_folder = wato_main_folder / "lvl1_aaa"
    wato_lvl1a_folder.mkdir(parents=True, exist_ok=True)
    _add_host_in_folder(wato_lvl1a_folder, "lvl1aaa-host")
    _add_rule_in_folder(wato_lvl1a_folder, "LVL1aaa")

    wato_lvl2_folder = wato_main_folder / "lvl1" / "lvl2"
    wato_lvl2_folder.mkdir(parents=True, exist_ok=True)
    _add_host_in_folder(wato_lvl2_folder, "lvl2-host")
    _add_rule_in_folder(wato_lvl2_folder, "LVL2")

    config.load()

    yield

    # Cleanup after the test. Would be better to use a dedicated test directory
    Path(cmk.utils.paths.main_config_file).unlink()
    (wato_main_folder / "hosts.mk").unlink()
    (wato_main_folder / "rules.mk").unlink()
    (wato_lvl1_folder / "hosts.mk").unlink()
    (wato_lvl1_folder / "rules.mk").unlink()
    (wato_lvl1a_folder / "hosts.mk").unlink()
    (wato_lvl1a_folder / "rules.mk").unlink()
    (wato_lvl2_folder / "hosts.mk").unlink()
    (wato_lvl2_folder / "rules.mk").unlink()
    (config._initialize_config())


def _add_host_in_folder(folder_path, name):
    with (folder_path / "hosts.mk").open("w", encoding="utf-8") as f:
        f.write(u"""
all_hosts += ['%(name)s']

host_tags.update({'%(name)s': {}})

ipaddresses.update({'%(name)s': '127.0.0.1'})

host_tags.update({
    '%(name)s': {
        'piggyback': 'auto-piggyback',
        'networking': 'lan',
        'agent': 'cmk-agent',
        'criticality': 'prod',
        'snmp_ds': 'no-snmp',
        'ip-v4': 'ip-v4',
        'ip-v6': 'ip-v6',
        'site': 'unit',
        'tcp': 'tcp',
        'address_family': 'ip-v4v6',
    }
})
""" % {"name": name})


def _add_rule_in_folder(folder_path, value):
    with (folder_path / "rules.mk").open("w", encoding="utf-8") as f:
        if value == "LVL0":
            condition = "{}"
        else:
            condition = "{'host_folder': '/%s/' % FOLDER_PATH}"

        f.write(u"""
cmc_host_rrd_config = [
{'condition': %s, 'value': '%s'},
] + cmc_host_rrd_config
""" % (condition, value))


@pytest.fixture(name="serial")
def fixture_serial():
    return ConfigSerial("13")


def test_save_packed_config(monkeypatch, serial):
    ts = Scenario()
    ts.add_host("bla1")
    config_cache = ts.apply(monkeypatch)

    assert not Path(cmk.utils.paths.core_helper_config_dir, serial,
                    "precompiled_check_config.mk").exists()

    config.save_packed_config(serial, config_cache)

    assert Path(cmk.utils.paths.core_helper_config_dir, serial,
                "precompiled_check_config.mk").exists()


def test_load_packed_config(serial):
    config.PackedConfigStore(serial).write({"abc": 1})

    assert "abc" not in config.__dict__
    config.load_packed_config(serial)
    # Mypy does not understand that we add some new member for testing
    assert config.abc == 1  # type: ignore[attr-defined]
    del config.__dict__["abc"]


class TestPackedConfigStore:
    @pytest.fixture()
    def store(self, serial):
        return config.PackedConfigStore(serial)

    def test_latest_serial_path(self):
        store = config.PackedConfigStore(serial=LATEST_SERIAL)
        assert store.path == Path(cmk.utils.paths.core_helper_config_dir, "latest",
                                  "precompiled_check_config.mk")

    def test_given_serial_path(self):
        store = config.PackedConfigStore(serial=ConfigSerial("42"))
        assert store.path == Path(cmk.utils.paths.core_helper_config_dir, "42",
                                  "precompiled_check_config.mk")

    def test_read_not_existing_file(self, store):
        with pytest.raises(FileNotFoundError):
            store.read()

    def test_write(self, store, serial):
        assert not Path(cmk.utils.paths.core_helper_config_dir, serial,
                        "precompiled_check_config.mk").exists()

        store.write({"abc": 1})

        packed_file_path = Path(cmk.utils.paths.core_helper_config_dir, serial,
                                "precompiled_check_config.mk")
        assert packed_file_path.exists()

        assert store.read() == {
            "abc": 1,
        }


@pytest.mark.parametrize("params, expected_result", [
    (
        None,
        False,
    ),
    (
        {},
        False,
    ),
    (
        {
            'x': 'y'
        },
        False,
    ),
    (
        [1, (2, 3)],
        False,
    ),
    (
        4,
        False,
    ),
    (
        {
            'tp_default_value': 1,
            'tp_values': [('24X7', 2)]
        },
        True,
    ),
    (
        ['abc', {
            'tp_default_value': 1,
            'tp_values': [('24X7', 2)]
        }],
        True,
    ),
])
def test_has_timespecific_params(params, expected_result):
    assert config.has_timespecific_params(params) is expected_result


def test__extract_check_plugins(monkeypatch):
    duplicate_plugin = {
        "duplicate_plugin": {
            "service_description": "blah",
        },
    }
    registered_plugin = CheckPlugin(
        CheckPluginName("duplicate_plugin"),
        [],
        "Duplicate Plugin",
        None,  # type: ignore  # irrelevant for test
        None,  # type: ignore  # irrelevant for test
        None,  # type: ignore  # irrelevant for test
        None,  # type: ignore  # irrelevant for test
        None,  # type: ignore  # irrelevant for test
        None,  # type: ignore  # irrelevant for test
        None,  # type: ignore  # irrelevant for test
        None,  # type: ignore  # irrelevant for test
        None,  # type: ignore  # irrelevant for test
    )

    monkeypatch.setattr(
        agent_based_register._config,
        "registered_check_plugins",
        {registered_plugin.name: registered_plugin},
    )
    monkeypatch.setattr(
        config,
        "check_info",
        duplicate_plugin,
    )
    monkeypatch.setattr(
        cmk.utils.debug,
        "enabled",
        lambda: True,
    )

    assert agent_based_register.is_registered_check_plugin(CheckPluginName("duplicate_plugin"))
    with pytest.raises(MKGeneralException):
        config._extract_check_plugins(validate_creation_kwargs=False)


def test__extract_agent_and_snmp_sections(monkeypatch):
    duplicate_plugin = {  # type: ignore
        "duplicate_plugin": {},
    }
    registered_section = SNMPSectionPlugin(
        SectionName("duplicate_plugin"),
        ParsedSectionName("duplicate_plugin"),
        None,  # type: ignore  # irrelevant for test
        None,  # type: ignore  # irrelevant for test
        None,  # type: ignore  # irrelevant for test
        None,  # type: ignore  # irrelevant for test
        None,  # type: ignore  # irrelevant for test
        None,  # type: ignore  # irrelevant for test
        None,  # type: ignore  # irrelevant for test
        None,  # type: ignore  # irrelevant for test
        None,  # type: ignore  # irrelevant for test
    )

    monkeypatch.setattr(
        agent_based_register._config,
        "registered_snmp_sections",
        {registered_section.name: registered_section},
    )
    monkeypatch.setattr(
        config,
        "check_info",
        duplicate_plugin,
    )
    monkeypatch.setattr(
        cmk.utils.debug,
        "enabled",
        lambda: True,
    )

    assert agent_based_register.is_registered_section_plugin(SectionName("duplicate_plugin"))
    config._extract_agent_and_snmp_sections(validate_creation_kwargs=False)
    assert agent_based_register.get_section_plugin(
        SectionName("duplicate_plugin")) == registered_section
