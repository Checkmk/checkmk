#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import shutil
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Sequence, Tuple, Union

import pytest
from _pytest.monkeypatch import MonkeyPatch

from tests.testlib.base import Scenario

import cmk.utils.paths
import cmk.utils.piggyback as piggyback
import cmk.utils.version as cmk_version
from cmk.utils.caching import config_cache as _config_cache
from cmk.utils.config_path import VersionedConfigPath
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.parameters import TimespecificParameters, TimespecificParameterSet
from cmk.utils.rulesets.ruleset_matcher import RulesetMatchObject
from cmk.utils.type_defs import (
    CheckPluginName,
    HostKey,
    HostName,
    RuleSetName,
    SectionName,
    SourceType,
)

from cmk.core_helpers.type_defs import Mode

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.config as config
from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.type_defs import HostLabel, ParsedSectionName, SNMPSectionPlugin
from cmk.base.autochecks import AutocheckEntry
from cmk.base.check_utils import ConfiguredService


def test_duplicate_hosts(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    for hostname in map(HostName, ["bla1", "bla1", "zzz", "zzz", "yyy"]):
        ts.add_host(hostname)
    ts.apply(monkeypatch)
    assert config.duplicate_hosts() == ["bla1", "zzz"]


def test_all_offline_hosts(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    ts.add_host(HostName("blub"), tags={"criticality": "offline"})
    ts.add_host(HostName("bla"))
    ts.apply(monkeypatch)
    assert config.all_offline_hosts() == set()


def test_all_offline_hosts_with_wato_default_config(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario(site_id="site1")
    ts.set_ruleset(
        "only_hosts",
        [
            (["!offline"], config.ALL_HOSTS),
        ],
    )
    ts.add_host(HostName("blub1"), tags={"criticality": "offline"})
    ts.add_host(HostName("blub2"), tags={"criticality": "offline", "site": "site2"})
    ts.add_host(HostName("bla"))
    ts.apply(monkeypatch)
    assert config.all_offline_hosts() == {"blub1"}


def test_all_configured_offline_hosts(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario(site_id="site1")
    ts.set_ruleset(
        "only_hosts",
        [
            (["!offline"], config.ALL_HOSTS),
        ],
    )
    ts.add_host(HostName("blub1"), tags={"criticality": "offline", "site": "site1"})
    ts.add_host(HostName("blub2"), tags={"criticality": "offline", "site": "site2"})
    ts.apply(monkeypatch)
    assert config.all_offline_hosts() == {"blub1"}


def test_all_configured_hosts(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario(site_id="site1")
    ts.add_host(HostName("real1"), tags={"site": "site1"})
    ts.add_host(HostName("real2"), tags={"site": "site2"})
    ts.add_host(HostName("real3"))
    ts.add_cluster(HostName("cluster1"), tags={"site": "site1"}, nodes=["node1"])
    ts.add_cluster(HostName("cluster2"), tags={"site": "site2"}, nodes=["node2"])
    ts.add_cluster(HostName("cluster3"), nodes=["node3"])

    config_cache = ts.apply(monkeypatch)
    assert config_cache.all_configured_clusters() == {
        HostName(c) for c in ("cluster1", "cluster2", "cluster3")
    }
    assert config_cache.all_configured_realhosts() == {
        HostName(h) for h in ("real1", "real2", "real3")
    }
    assert config_cache.all_configured_hosts() == {
        HostName(h) for h in ("cluster1", "cluster2", "cluster3", "real1", "real2", "real3")
    }


def test_all_active_hosts(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario(site_id="site1")
    ts.add_host(HostName("real1"), tags={"site": "site1"})
    ts.add_host(HostName("real2"), tags={"site": "site2"})
    ts.add_host(HostName("real3"))
    ts.add_cluster(HostName("cluster1"), tags={"site": "site1"}, nodes=["node1"])
    ts.add_cluster(HostName("cluster2"), tags={"site": "site2"}, nodes=["node2"])
    ts.add_cluster(HostName("cluster3"), nodes=["node3"])

    config_cache = ts.apply(monkeypatch)
    assert config_cache.all_active_clusters() == {HostName(c) for c in ("cluster1", "cluster3")}
    assert config_cache.all_active_realhosts() == {HostName(h) for h in ("real1", "real3")}
    assert config_cache.all_active_hosts() == {
        HostName(h) for h in ("cluster1", "cluster3", "real1", "real3")
    }


def test_config_cache_tag_to_group_map(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    ts.set_option(
        "tag_config",
        {
            "aux_tags": [],
            "tag_groups": [
                {
                    "id": "dingeling",
                    "title": "Dung",
                    "tags": [
                        {"aux_tags": [], "id": "dong", "title": "ABC"},
                    ],
                }
            ],
        },
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_tag_to_group_map() == {
        "all-agents": "agent",
        "auto-piggyback": "piggyback",
        "cmk-agent": "agent",
        "checkmk-agent": "checkmk-agent",
        "dong": "dingeling",
        "ip-v4": "ip-v4",
        "ip-v4-only": "address_family",
        "ip-v4v6": "address_family",
        "ip-v6": "ip-v6",
        "ip-v6-only": "address_family",
        "no-agent": "agent",
        "no-ip": "address_family",
        "no-piggyback": "piggyback",
        "no-snmp": "snmp_ds",
        "piggyback": "piggyback",
        "ping": "ping",
        "snmp": "snmp",
        "snmp-v1": "snmp_ds",
        "snmp-v2": "snmp_ds",
        "special-agents": "agent",
        "tcp": "tcp",
    }


@pytest.mark.parametrize(
    "hostname_str,host_path,result",
    [
        ("none", "/hosts.mk", 0),
        ("main", "/wato/hosts.mk", 0),
        ("sub1", "/wato/level1/hosts.mk", 1),
        ("sub2", "/wato/level1/level2/hosts.mk", 2),
        ("sub3", "/wato/level1/level3/hosts.mk", 3),
        ("sub11", "/wato/level11/hosts.mk", 11),
        ("sub22", "/wato/level11/level22/hosts.mk", 22),
    ],
)
def test_host_folder_matching(
    monkeypatch: MonkeyPatch, hostname_str: str, host_path: str, result: int
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname, host_path=host_path)
    ts.set_ruleset(
        "agent_ports",
        [
            (22, ["/wato/level11/level22/+"], config.ALL_HOSTS),
            (11, ["/wato/level11/+"], config.ALL_HOSTS),
            (3, ["/wato/level1/level3/+"], config.ALL_HOSTS),
            (2, ["/wato/level1/level2/+"], config.ALL_HOSTS),
            (1, ["/wato/level1/+"], config.ALL_HOSTS),
            (0, [], config.ALL_HOSTS),
        ],
    )

    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).agent_port == result


@pytest.mark.parametrize(
    "hostname_str,tags,result",
    [
        ("testhost", {}, True),
        ("testhost", {"address_family": "ip-v4-only"}, True),
        ("testhost", {"address_family": "ip-v4v6"}, True),
        ("testhost", {"address_family": "ip-v6-only"}, False),
        ("testhost", {"address_family": "no-ip"}, False),
    ],
)
def test_is_ipv4_host(
    monkeypatch: MonkeyPatch, hostname_str: str, tags: Dict[str, str], result: bool
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname, tags)
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_ipv4_host == result


@pytest.mark.parametrize(
    "hostname_str,tags,result",
    [
        ("testhost", {}, False),
        ("testhost", {"address_family": "ip-v4-only"}, False),
        ("testhost", {"address_family": "ip-v4v6"}, True),
        ("testhost", {"address_family": "ip-v6-only"}, True),
        ("testhost", {"address_family": "no-ip"}, False),
    ],
)
def test_is_ipv6_host(
    monkeypatch: MonkeyPatch, hostname_str: str, tags: Dict[str, str], result: bool
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname, tags)
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_ipv6_host == result


@pytest.mark.parametrize(
    "hostname_str,tags,result",
    [
        ("testhost", {}, False),
        ("testhost", {"address_family": "ip-v4-only"}, False),
        ("testhost", {"address_family": "ip-v4v6"}, True),
        ("testhost", {"address_family": "ip-v6-only"}, False),
        ("testhost", {"address_family": "no-ip"}, False),
    ],
)
def test_is_ipv4v6_host(
    monkeypatch: MonkeyPatch, hostname_str: str, tags: Dict[str, str], result: bool
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname, tags)
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_ipv4v6_host == result


@pytest.mark.parametrize(
    "hostname_str,tags,result",
    [
        ("testhost", {"piggyback": "piggyback"}, True),
        ("testhost", {"piggyback": "no-piggyback"}, False),
    ],
)
def test_is_piggyback_host(
    monkeypatch: MonkeyPatch, hostname_str: str, tags: Dict[str, str], result: bool
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname, tags)
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_piggyback_host == result


@pytest.mark.parametrize(
    "with_data,result",
    [
        (True, True),
        (False, False),
    ],
)
@pytest.mark.parametrize(
    "hostname_str,tags",
    [
        ("testhost", {}),
        ("testhost", {"piggyback": "auto-piggyback"}),
    ],
)
def test_is_piggyback_host_auto(
    monkeypatch: MonkeyPatch, hostname_str: str, tags: Dict[str, str], with_data: bool, result: bool
) -> None:
    hostname = HostName(hostname_str)
    monkeypatch.setattr(piggyback, "has_piggyback_raw_data", lambda hostname, cache_age: with_data)
    ts = Scenario()
    ts.add_host(hostname, tags)
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_piggyback_host == result


@pytest.mark.parametrize(
    "hostname_str,tags,result",
    [
        ("testhost", {}, False),
        ("testhost", {"address_family": "ip-v4-only"}, False),
        ("testhost", {"address_family": "ip-v4v6"}, False),
        ("testhost", {"address_family": "ip-v6-only"}, False),
        ("testhost", {"address_family": "no-ip"}, True),
    ],
)
def test_is_no_ip_host(
    monkeypatch: MonkeyPatch, hostname_str: str, tags: Dict[str, str], result: bool
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname, tags)
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_no_ip_host == result


@pytest.mark.parametrize(
    "hostname_str,tags,result,ruleset",
    [
        ("testhost", {}, False, []),
        (
            "testhost",
            {"address_family": "ip-v4-only"},
            False,
            [
                ("ipv6", [], config.ALL_HOSTS, {}),
            ],
        ),
        ("testhost", {"address_family": "ip-v4v6"}, False, []),
        (
            "testhost",
            {"address_family": "ip-v4v6"},
            True,
            [
                ("ipv6", [], config.ALL_HOSTS, {}),
            ],
        ),
        ("testhost", {"address_family": "ip-v6-only"}, True, []),
        (
            "testhost",
            {"address_family": "ip-v6-only"},
            True,
            [
                ("ipv4", [], config.ALL_HOSTS, {}),
            ],
        ),
        (
            "testhost",
            {"address_family": "ip-v6-only"},
            True,
            [
                ("ipv6", [], config.ALL_HOSTS, {}),
            ],
        ),
        ("testhost", {"address_family": "no-ip"}, False, []),
    ],
)
def test_is_ipv6_primary_host(
    monkeypatch: MonkeyPatch, hostname_str: str, tags: Dict[str, str], result: bool, ruleset: List
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname, tags)
    ts.set_ruleset("primary_address_family", ruleset)
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_ipv6_primary == result


@pytest.mark.parametrize(
    "result,attrs",
    [
        ("127.0.1.1", {}),
        ("127.0.1.1", {"management_address": ""}),
        ("127.0.0.1", {"management_address": "127.0.0.1"}),
        ("lolo", {"management_address": "lolo"}),
    ],
)
def test_host_config_management_address(
    monkeypatch: MonkeyPatch, attrs: Dict[str, str], result: str
) -> None:
    hostname = HostName("hostname")
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option("ipaddresses", {hostname: "127.0.1.1"})
    ts.set_option("host_attributes", {hostname: attrs})
    config_cache = ts.apply(monkeypatch)

    assert config_cache.get_host_config(hostname).management_address == result


def _management_config_ruleset() -> List[Dict[str, Any]]:
    return [
        {"condition": {}, "value": ("snmp", "eee")},
        {"condition": {}, "value": ("ipmi", {"username": "eee", "password": "eee"})},
    ]


@pytest.mark.parametrize(
    "expected_result,protocol,credentials,ruleset",
    [
        (None, None, None, []),
        ("public", "snmp", None, []),
        (None, "ipmi", None, []),
        ("aaa", "snmp", "aaa", []),
        (
            {"username": "aaa", "password": "aaa"},
            "ipmi",
            {"username": "aaa", "password": "aaa"},
            [],
        ),
        (None, None, None, _management_config_ruleset()),
        ("eee", "snmp", None, _management_config_ruleset()),
        ({"username": "eee", "password": "eee"}, "ipmi", None, _management_config_ruleset()),
        ("aaa", "snmp", "aaa", _management_config_ruleset()),
        (
            {"username": "aaa", "password": "aaa"},
            "ipmi",
            {"username": "aaa", "password": "aaa"},
            _management_config_ruleset(),
        ),
    ],
)
def test_host_config_management_credentials(
    monkeypatch: MonkeyPatch,
    protocol: Optional[str],
    credentials: Optional[Dict[str, str]],
    expected_result: Optional[Union[str, Dict[str, str]]],
    ruleset: List,
):
    hostname = HostName("hostname")
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option("host_attributes", {hostname: {"management_address": "127.0.0.1"}})
    ts.set_option("management_protocol", {hostname: protocol})

    if credentials is not None:
        if protocol == "snmp":
            ts.set_option("management_snmp_credentials", {hostname: credentials})
        elif protocol == "ipmi":
            ts.set_option("management_ipmi_credentials", {hostname: credentials})
        else:
            raise NotImplementedError()

    ts.set_ruleset("management_board_config", ruleset)
    config_cache = ts.apply(monkeypatch)
    host_config = config_cache.get_host_config(hostname)

    assert host_config.management_credentials == expected_result

    # Test management_snmp_config on the way...
    if protocol == "snmp":
        assert host_config.management_snmp_config.credentials == expected_result


@pytest.mark.parametrize(
    "attrs,result",
    [
        ({}, ([], [])),
        (
            {
                "additional_ipv4addresses": ["10.10.10.10"],
                "additional_ipv6addresses": ["::3"],
            },
            (["10.10.10.10"], ["::3"]),
        ),
    ],
)
def test_host_config_additional_ipaddresses(
    monkeypatch: MonkeyPatch, attrs: Dict[str, List[str]], result: Tuple[List[str], List[str]]
) -> None:
    hostname = HostName("hostname")
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option("ipaddresses", {hostname: "127.0.1.1"})
    ts.set_option("host_attributes", {hostname: attrs})
    config_cache = ts.apply(monkeypatch)

    assert config_cache.get_host_config(hostname).additional_ipaddresses == result


@pytest.mark.parametrize(
    "hostname_str,tags,result",
    [
        ("testhost", {}, True),
        ("testhost", {"agent": "cmk-agent"}, True),
        ("testhost", {"agent": "cmk-agent", "snmp_ds": "snmp-v2"}, True),
        ("testhost", {"agent": "no-agent"}, False),
        ("testhost", {"agent": "no-agent", "snmp_ds": "no-snmp"}, False),
    ],
)
def test_is_tcp_host(
    monkeypatch: MonkeyPatch, hostname_str: str, tags: Dict[str, str], result: bool
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname, tags)
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_tcp_host == result


@pytest.mark.parametrize(
    "hostname_str,tags,result",
    [
        ("testhost", {}, False),
        ("testhost", {"agent": "cmk-agent"}, False),
        ("testhost", {"agent": "cmk-agent", "snmp_ds": "snmp-v1"}, False),
        ("testhost", {"snmp_ds": "snmp-v1"}, False),
        (
            "testhost",
            {"agent": "no-agent", "snmp_ds": "no-snmp", "piggyback": "no-piggyback"},
            True,
        ),
        ("testhost", {"agent": "no-agent", "snmp_ds": "no-snmp"}, True),
        ("testhost", {"agent": "no-agent"}, True),
    ],
)
def test_is_ping_host(
    monkeypatch: MonkeyPatch, hostname_str: str, tags: Dict[str, str], result: bool
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname, tags)
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_ping_host == result


@pytest.mark.parametrize(
    "hostname_str,tags,result",
    [
        ("testhost", {}, False),
        ("testhost", {"agent": "cmk-agent"}, False),
        ("testhost", {"agent": "cmk-agent", "snmp_ds": "snmp-v1"}, True),
        ("testhost", {"agent": "cmk-agent", "snmp_ds": "snmp-v2"}, True),
        ("testhost", {"agent": "cmk-agent", "snmp_ds": "no-snmp"}, False),
    ],
)
def test_is_snmp_host(
    monkeypatch: MonkeyPatch, hostname_str: str, tags: Dict[str, str], result: bool
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname, tags)
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_snmp_host == result


def test_is_not_usewalk_host(monkeypatch: MonkeyPatch) -> None:
    hostname = HostName("xyz")
    ts = Scenario()
    ts.add_host(hostname)
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_usewalk_host is False


def test_is_usewalk_host(monkeypatch: MonkeyPatch) -> None:
    hostname = HostName("xyz")
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "usewalk_hosts",
        [
            ([hostname], config.ALL_HOSTS, {}),
        ],
    )

    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_usewalk_host is False


@pytest.mark.parametrize(
    "hostname_str,tags,result",
    [
        ("testhost", {}, False),
        ("testhost", {"agent": "cmk-agent"}, False),
        ("testhost", {"agent": "no-agent", "snmp_ds": "snmp-v1"}, False),
        ("testhost", {"agent": "no-agent", "snmp_ds": "no-snmp"}, False),
        ("testhost", {"agent": "cmk-agent", "snmp_ds": "snmp-v1"}, True),
    ],
)
def test_is_dual_host(
    monkeypatch: MonkeyPatch, hostname_str: str, tags: Dict[str, str], result: bool
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname, tags)
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_dual_host == result


@pytest.mark.parametrize(
    "hostname_str,tags,result",
    [
        ("testhost", {}, False),
        ("testhost", {"agent": "all-agents"}, True),
        ("testhost", {"agent": "special-agents"}, False),
        ("testhost", {"agent": "no-agent"}, False),
        ("testhost", {"agent": "cmk-agent"}, False),
    ],
)
def test_is_all_agents_host(
    monkeypatch: MonkeyPatch, hostname_str: str, tags: Dict[str, str], result: bool
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname, tags)
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_all_agents_host == result


@pytest.mark.parametrize(
    "hostname_str,tags,result",
    [
        ("testhost", {}, False),
        ("testhost", {"agent": "all-agents"}, False),
        ("testhost", {"agent": "special-agents"}, True),
        ("testhost", {"agent": "no-agent"}, False),
        ("testhost", {"agent": "cmk-agent"}, False),
    ],
)
def test_is_all_special_agents_host(
    monkeypatch: MonkeyPatch, hostname_str: str, tags: Dict[str, str], result: bool
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname, tags)
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).is_all_special_agents_host == result


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", 6556),
        ("testhost2", 1337),
    ],
)
def test_host_config_agent_port(monkeypatch: MonkeyPatch, hostname_str: str, result: int) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "agent_ports",
        [
            (1337, [], ["testhost2"], {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).agent_port == result


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", 5.0),
        ("testhost2", 12.0),
    ],
)
def test_host_config_tcp_connect_timeout(
    monkeypatch: MonkeyPatch, hostname_str: str, result: float
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "tcp_connect_timeouts",
        [
            (12.0, [], ["testhost2"], {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).tcp_connect_timeout == result


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", {"use_regular": "disable", "use_realtime": "enforce"}),
        ("testhost2", {"use_regular": "enforce", "use_realtime": "disable"}),
    ],
)
def test_host_config_agent_encryption(
    monkeypatch: MonkeyPatch, hostname_str: str, result: Dict[str, str]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "agent_encryption",
        [
            ({"use_regular": "enforce", "use_realtime": "disable"}, [], ["testhost2"], {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).agent_encryption == result


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", None),
        ("testhost2", cmk_version.__version__),
    ],
)
def test_host_config_agent_target_version(
    monkeypatch: MonkeyPatch, hostname_str: str, result: Optional[str]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "check_mk_agent_target_versions",
        [
            ("site", [], ["testhost2"], {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).agent_target_version == result


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", None),
        ("testhost2", "echo 1"),
    ],
)
def test_host_config_datasource_program(
    monkeypatch: MonkeyPatch, hostname_str: str, result: Optional[str]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "datasource_programs",
        [
            ("echo 1", [], ["testhost2"], {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).datasource_program == result


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", []),
        (
            "testhost2",
            [
                ("abc", {"param1": 1}),
                ("xyz", {"param2": 1}),
            ],
        ),
    ],
)
def test_host_config_special_agents(
    monkeypatch: MonkeyPatch, hostname_str: str, result: List[Tuple]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option(
        "special_agents",
        {
            "abc": [
                ({"param1": 1}, [], ["testhost2"], {}),
            ],
            "xyz": [
                ({"param2": 1}, [], ["testhost2"], {}),
            ],
        },
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).special_agents == result


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", None),
        ("testhost2", ["127.0.0.1"]),
    ],
)
def test_host_config_only_from(
    monkeypatch: MonkeyPatch, hostname_str: str, result: List[str]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option(
        "agent_config",
        {
            "only_from": [
                (
                    [
                        "127.0.0.1",
                    ],
                    [],
                    ["testhost2"],
                    {},
                ),
                (
                    [
                        "127.0.0.2",
                    ],
                    [],
                    ["testhost2"],
                    {},
                ),
            ],
        },
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).only_from == result


@pytest.mark.parametrize(
    "hostname_str,core_name,result",
    [
        ("testhost1", "cmc", None),
        ("testhost2", "cmc", "command1"),
        ("testhost3", "cmc", "smart"),
        ("testhost3", "nagios", "ping"),
    ],
)
def test_host_config_explicit_check_command(
    monkeypatch: MonkeyPatch, hostname_str: str, core_name: str, result: Optional[str]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
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


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", {}),
        ("testhost2", {"ding": 1, "dong": 1}),
    ],
)
def test_host_config_ping_levels(
    monkeypatch: MonkeyPatch, hostname_str: str, result: Dict[str, int]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "ping_levels",
        [
            (
                {
                    "ding": 1,
                },
                [],
                ["testhost2"],
                {},
            ),
            (
                {
                    "ding": 3,
                },
                [],
                ["testhost2"],
                {},
            ),
            (
                {
                    "dong": 1,
                },
                [],
                ["testhost2"],
                {},
            ),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).ping_levels == result


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", []),
        ("testhost2", ["icon1", "icon2"]),
    ],
)
def test_host_config_icons_and_actions(
    monkeypatch: MonkeyPatch, hostname_str: str, result: List[str]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "host_icons_and_actions",
        [
            ("icon1", [], ["testhost2"], {}),
            ("icon1", [], ["testhost2"], {}),
            ("icon2", [], ["testhost2"], {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert sorted(config_cache.get_host_config(hostname).icons_and_actions) == sorted(result)


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", {}),
        ("testhost2", {"_CUSTOM": ["value1"], "dingdong": ["value1"]}),
    ],
)
def test_host_config_extra_host_attributes(
    monkeypatch: MonkeyPatch, hostname_str: str, result: Dict[str, List[str]]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option(
        "extra_host_conf",
        {
            "dingdong": [
                (
                    [
                        "value1",
                    ],
                    [],
                    ["testhost2"],
                    {},
                ),
                (
                    [
                        "value2",
                    ],
                    [],
                    ["testhost2"],
                    {},
                ),
            ],
            "_custom": [
                (
                    [
                        "value1",
                    ],
                    [],
                    ["testhost2"],
                    {},
                ),
                (
                    [
                        "value2",
                    ],
                    [],
                    ["testhost2"],
                    {},
                ),
            ],
        },
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).extra_host_attributes == result


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", {}),
        (
            "testhost2",
            {
                "value1": 1,
                "value2": 2,
            },
        ),
    ],
)
def test_host_config_inventory_parameters(
    monkeypatch: MonkeyPatch, hostname_str: str, result: Dict[str, int]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option(
        "inv_parameters",
        {
            "if": [
                (
                    {
                        "value1": 1,
                    },
                    [],
                    ["testhost2"],
                    {},
                ),
                (
                    {
                        "value2": 2,
                    },
                    [],
                    ["testhost2"],
                    {},
                ),
            ],
        },
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).inventory_parameters(RuleSetName("if")) == result


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        (
            "testhost1",
            None,
        ),
        (
            "testhost2",
            config.DiscoveryCheckParameters(
                check_interval=1,
                severity_new_services=1,
                severity_vanished_services=0,
                severity_new_host_labels=1,
                rediscovery={},
            ),
        ),
    ],
)
def test_host_config_discovery_check_parameters(
    monkeypatch: MonkeyPatch, hostname_str: str, result: Optional[config.DiscoveryCheckParameters]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option(
        "periodic_discovery",
        [
            (
                {
                    "check_interval": 1,
                    "severity_unmonitored": 1,
                    "severity_vanished": 0,
                    "severity_new_host_label": 1,
                },
                [],
                ["testhost2"],
                {},
            ),
            (
                {
                    "check_interval": 2,
                    "severity_unmonitored": 1,
                    "severity_vanished": 0,
                    "severity_new_host_label": 1,
                },
                [],
                ["testhost2"],
                {},
            ),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    params = config_cache.get_host_config(hostname).discovery_check_parameters

    if result is None:
        assert params is None or params.check_interval is None
    else:
        assert params == result


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", []),
        (
            "testhost2",
            [
                ("abc", {"param1": 1}),
                ("xyz", {"param2": 1}),
            ],
        ),
    ],
)
def test_host_config_inventory_export_hooks(
    monkeypatch: MonkeyPatch, hostname_str: str, result: List[Tuple]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option(
        "inv_exports",
        {
            "abc": [
                ({"param1": 1}, [], ["testhost2"], {}),
            ],
            "xyz": [
                ({"param2": 1}, [], ["testhost2"], {}),
            ],
        },
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).inventory_export_hooks == result


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", {}),
        (
            "testhost2",
            {
                "value1": 1,
                "value2": 2,
            },
        ),
    ],
)
def test_host_config_notification_plugin_parameters(
    monkeypatch: MonkeyPatch, hostname_str: str, result: Dict[str, int]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option(
        "notification_parameters",
        {
            "mail": [
                (
                    {
                        "value1": 1,
                    },
                    [],
                    ["testhost2"],
                    {},
                ),
                (
                    {
                        "value1": 2,
                        "value2": 2,
                    },
                    [],
                    ["testhost2"],
                    {},
                ),
            ],
        },
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).notification_plugin_parameters("mail") == result


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", []),
        (
            "testhost2",
            [
                (
                    "abc",
                    [{"param1": 1}, {"param2": 2}],
                ),
                (
                    "xyz",
                    [
                        {"param2": 1},
                    ],
                ),
            ],
        ),
    ],
)
def test_host_config_active_checks(
    monkeypatch: MonkeyPatch, hostname_str: str, result: List[Tuple]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option(
        "active_checks",
        {
            "abc": [
                ({"param1": 1}, [], ["testhost2"], {}),
                ({"param2": 2}, [], ["testhost2"], {}),
            ],
            "xyz": [
                ({"param2": 1}, [], ["testhost2"], {}),
            ],
        },
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).active_checks == result


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", []),
        ("testhost2", [{"param1": 1}, {"param2": 2}]),
    ],
)
def test_host_config_custom_checks(
    monkeypatch: MonkeyPatch, hostname_str: str, result: List[Dict[str, int]]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "custom_checks",
        [
            ({"param1": 1}, [], ["testhost2"], {}),
            ({"param2": 2}, [], ["testhost2"], {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).custom_checks == result


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", []),
        (
            "testhost2",
            [
                (
                    "checkgroup",
                    CheckPluginName("checktype1"),
                    "item1",
                    TimespecificParameterSet({"param1": 1}, ()),
                ),
                (
                    "checkgroup",
                    CheckPluginName("checktype2"),
                    "item2",
                    TimespecificParameterSet({"param2": 2}, ()),
                ),
            ],
        ),
    ],
)
def test_host_config_static_checks(
    monkeypatch: MonkeyPatch, hostname_str: str, result: List[Tuple]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option(
        "static_checks",
        {
            "checkgroup": [
                (("checktype1", "item1", {"param1": 1}), [], ["testhost2"], {}),
                (("checktype2", "item2", {"param2": 2}), [], ["testhost2"], {}),
            ],
        },
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).static_checks == result


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", ["check_mk"]),
        ("testhost2", ["dingdong"]),
    ],
)
def test_host_config_hostgroups(
    monkeypatch: MonkeyPatch, hostname_str: str, result: List[str]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "host_groups",
        [
            ("dingdong", [], ["testhost2"], {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).hostgroups == result


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        # No rule matches for this host
        ("testhost1", []),
        # Take the group from the ruleset (dingdong) and the definition from the nearest folder in
        # the hierarchy (abc). Don't apply the definition from the parent folder (xyz).
        ("testhost2", ["abc", "dingdong"]),
        # Take the group from all rulesets (dingdong, haha) and the definition from the nearest
        # folder in the hierarchy (abc). Don't apply the definition from the parent folder (xyz).
        ("testhost3", ["abc", "dingdong", "haha"]),
    ],
)
def test_host_config_contactgroups(
    monkeypatch: MonkeyPatch, hostname_str: str, result: List[str]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "host_contactgroups",
        [
            # Seems both, a list of groups and a group name is allowed. We should clean
            # this up to be always a list of groups in the future...
            ("dingdong", [], ["testhost2", "testhost3"], {}),
            (["abc"], [], ["testhost2", "testhost3"], {}),
            (["xyz"], [], ["testhost2", "testhost3"], {}),
            ("haha", [], ["testhost3"], {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert sorted(config_cache.get_host_config(hostname).contactgroups) == sorted(result)


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", {}),
        ("testhost2", {"empty_output": 1}),
    ],
)
def test_host_config_exit_code_spec_overall(
    monkeypatch: MonkeyPatch, hostname_str: str, result: Dict[str, int]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "check_mk_exit_status",
        [
            (
                {
                    "overall": {"empty_output": 1},
                    "individual": {"snmp": {"empty_output": 4}},
                },
                [],
                ["testhost2"],
                {},
            ),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).exit_code_spec() == result


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", {}),
        ("testhost2", {"empty_output": 4}),
    ],
)
def test_host_config_exit_code_spec_individual(
    monkeypatch: MonkeyPatch, hostname_str: str, result: Dict[str, int]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "check_mk_exit_status",
        [
            (
                {
                    "overall": {"empty_output": 1},
                    "individual": {"snmp": {"empty_output": 4}},
                },
                [],
                ["testhost2"],
                {},
            ),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).exit_code_spec(data_source_id="snmp") == result


@pytest.mark.parametrize(
    "ruleset",
    [
        {
            "empty_output": 2,
            "restricted_address_mismatch": 2,
        },
        {
            "overall": {
                "empty_output": 2,
            },
            "restricted_address_mismatch": 2,
        },
        {
            "individual": {
                "snmp": {
                    "empty_output": 2,
                }
            },
            "restricted_address_mismatch": 2,
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
            "restricted_address_mismatch": 2,
        },
    ],
)
def test_host_config_exit_code_spec(monkeypatch: MonkeyPatch, ruleset: Dict[str, Any]) -> None:
    hostname = HostName("hostname")
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "check_mk_exit_status",
        [
            (ruleset, [], ["hostname"], {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    host_config = config_cache.get_host_config(hostname)

    exit_code_spec = host_config.exit_code_spec()
    assert "restricted_address_mismatch" in exit_code_spec
    assert exit_code_spec["restricted_address_mismatch"] == 2

    result = {
        "empty_output": 2,
        "restricted_address_mismatch": 2,
    }
    snmp_exit_code_spec = host_config.exit_code_spec(data_source_id="snmp")
    assert snmp_exit_code_spec == result


@pytest.mark.parametrize(
    "hostname_str,version,result",
    [
        ("testhost1", 2, None),
        ("testhost2", 2, "bla"),
        ("testhost2", 3, ("noAuthNoPriv", "v3")),
        ("testhost3", 2, "bla"),
        ("testhost3", 3, None),
        ("testhost4", 2, None),
        ("testhost4", 3, ("noAuthNoPriv", "v3")),
    ],
)
def test_host_config_snmp_credentials_of_version(
    monkeypatch: MonkeyPatch,
    hostname_str: str,
    version: int,
    result: Union[None, str, Tuple[str, str]],
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "snmp_communities",
        [
            ("bla", [], ["testhost2", "testhost3"], {}),
            (("noAuthNoPriv", "v3"), [], ["testhost2", "testhost4"], {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).snmp_credentials_of_version(version) == result


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize(
    "hostname_str,section_name,result",
    [
        ("testhost1", "uptime", None),
        ("testhost2", "uptime", None),
        ("testhost1", "snmp_uptime", None),
        ("testhost2", "snmp_uptime", 4),
    ],
)
def test_host_config_snmp_check_interval(
    monkeypatch: MonkeyPatch, hostname_str: str, section_name: str, result: Optional[int]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "snmp_check_interval",
        [
            (("snmp_uptime", 4), [], ["testhost2"], {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).snmp_fetch_interval(
        SectionName(section_name)
    ) == (60 * result if result else None)


def test_http_proxies() -> None:
    assert config.http_proxies == {}


@pytest.fixture(name="service_list")
def _service_list() -> List[ConfiguredService]:
    return [
        ConfiguredService(
            check_plugin_name=CheckPluginName("plugin_%s" % d),
            item="item",
            description="description %s" % d,
            parameters=TimespecificParameters(),
            discovered_parameters={},
            service_labels={},
        )
        for d in "FDACEB"
    ]


def test_get_sorted_check_table_cmc(
    monkeypatch: MonkeyPatch, service_list: List[ConfiguredService]
) -> None:
    monkeypatch.setattr(config, "is_cmc", lambda: True)

    assert service_list == config.resolve_service_dependencies(
        host_name=HostName("horst"),
        services=service_list,
    )


def test_get_sorted_check_table_no_cmc(
    monkeypatch: MonkeyPatch, service_list: List[ConfiguredService]
) -> None:
    monkeypatch.setattr(config, "is_cmc", lambda: False)
    monkeypatch.setattr(
        config,
        "service_depends_on",
        lambda _hn, descr: {
            "description A": ["description C"],
            "description B": ["description D"],
            "description D": ["description A", "description F"],
        }.get(descr, []),
    )

    sorted_service_list = config.resolve_service_dependencies(
        host_name=HostName("horst"),
        services=service_list,
    )
    assert [s.description for s in sorted_service_list] == [
        "description F",  #
        "description C",  # no deps => input order maintained
        "description E",  #
        "description A",
        "description D",
        "description B",
    ]


def test_resolve_service_dependencies_cyclic(
    monkeypatch: MonkeyPatch, service_list: List[ConfiguredService]
) -> None:
    monkeypatch.setattr(config, "is_cmc", lambda: False)
    monkeypatch.setattr(
        config,
        "service_depends_on",
        lambda _hn, descr: {
            "description A": ["description B"],
            "description B": ["description D"],
            "description D": ["description A"],
        }.get(descr, []),
    )

    with pytest.raises(
        MKGeneralException,
        match=re.escape(
            "Cyclic service dependency of host MyHost:"
            " 'description D' (plugin_D / item),"
            " 'description A' (plugin_A / item),"
            " 'description B' (plugin_B / item)"
        ),
    ):
        _ = config.resolve_service_dependencies(host_name=HostName("MyHost"), services=service_list)


def test_service_depends_on_unknown_host() -> None:
    assert config.service_depends_on(HostName("test-host"), "svc") == []


def test_service_depends_on(monkeypatch: MonkeyPatch) -> None:
    test_host = HostName("test-host")
    ts = Scenario()
    ts.add_host(test_host)
    ts.set_ruleset(
        "service_dependencies",
        [
            ("dep1", [], config.ALL_HOSTS, ["svc1"], {}),
            ("dep2-%s", [], config.ALL_HOSTS, ["svc1-(.*)"], {}),
            ("dep-disabled", [], config.ALL_HOSTS, ["svc1"], {"disabled": True}),
        ],
    )
    ts.apply(monkeypatch)

    assert config.service_depends_on(test_host, "svc2") == []
    assert config.service_depends_on(test_host, "svc1") == ["dep1"]
    assert config.service_depends_on(test_host, "svc1-abc") == ["dep1", "dep2-abc"]


@pytest.fixture(name="cluster_config")
def cluster_config_fixture(monkeypatch: MonkeyPatch) -> config.ConfigCache:
    ts = Scenario()
    ts.add_host(HostName("node1"))
    ts.add_host(HostName("host1"))
    ts.add_cluster(HostName("cluster1"), nodes=["node1"])
    return ts.apply(monkeypatch)


def test_host_config_is_cluster(cluster_config: config.ConfigCache) -> None:
    assert cluster_config.get_host_config(HostName("node1")).is_cluster is False
    assert cluster_config.get_host_config(HostName("host1")).is_cluster is False
    assert cluster_config.get_host_config(HostName("cluster1")).is_cluster is True


def test_host_config_part_of_clusters(cluster_config: config.ConfigCache) -> None:
    assert cluster_config.get_host_config(HostName("node1")).part_of_clusters == ["cluster1"]
    assert cluster_config.get_host_config(HostName("host1")).part_of_clusters == []
    assert cluster_config.get_host_config(HostName("cluster1")).part_of_clusters == []


def test_host_config_nodes(cluster_config: config.ConfigCache) -> None:
    assert cluster_config.get_host_config(HostName("node1")).nodes is None
    assert cluster_config.get_host_config(HostName("host1")).nodes is None
    assert cluster_config.get_host_config(HostName("cluster1")).nodes == ["node1"]


def test_host_config_parents(cluster_config: config.ConfigCache) -> None:
    assert cluster_config.get_host_config(HostName("node1")).parents == []
    assert cluster_config.get_host_config(HostName("host1")).parents == []
    # TODO: Move cluster/node parent handling to HostConfig
    # assert cluster_config.get_host_config("cluster1").parents == ["node1"]
    assert cluster_config.get_host_config(HostName("cluster1")).parents == []


def test_config_cache_tag_list_of_host(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    test_host = HostName("test-host")
    xyz_host = HostName("xyz")
    ts.add_host(test_host, tags={"agent": "no-agent"})
    ts.add_host(xyz_host)
    config_cache = ts.apply(monkeypatch)

    print(config_cache._hosttags[test_host])
    print(config_cache._hosttags[xyz_host])
    assert config_cache.tag_list_of_host(xyz_host) == {
        "/wato/",
        "lan",
        "ip-v4",
        "checkmk-agent",
        "cmk-agent",
        "no-snmp",
        "tcp",
        "auto-piggyback",
        "ip-v4-only",
        "site:unit",
        "prod",
    }


def test_config_cache_tag_list_of_host_not_existing(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    config_cache = ts.apply(monkeypatch)

    assert config_cache.tag_list_of_host(HostName("not-existing")) == {
        "/",
        "lan",
        "cmk-agent",
        "no-snmp",
        "auto-piggyback",
        "ip-v4-only",
        "site:NO_SITE",
        "prod",
    }


def test_host_tags_default() -> None:
    assert isinstance(config.host_tags, dict)


def test_host_tags_of_host(monkeypatch: MonkeyPatch) -> None:
    test_host = HostName("test-host")
    xyz_host = HostName("xyz")
    ts = Scenario()
    ts.add_host(test_host, tags={"agent": "no-agent"})
    ts.add_host(xyz_host)
    config_cache = ts.apply(monkeypatch)

    cfg = config_cache.get_host_config(xyz_host)
    assert cfg.tag_groups == {
        "address_family": "ip-v4-only",
        "agent": "cmk-agent",
        "criticality": "prod",
        "ip-v4": "ip-v4",
        "networking": "lan",
        "piggyback": "auto-piggyback",
        "site": "unit",
        "snmp_ds": "no-snmp",
        "tcp": "tcp",
        "checkmk-agent": "checkmk-agent",
    }
    assert config_cache.tags_of_host(xyz_host) == cfg.tag_groups

    cfg = config_cache.get_host_config(test_host)
    assert cfg.tag_groups == {
        "address_family": "ip-v4-only",
        "agent": "no-agent",
        "criticality": "prod",
        "ip-v4": "ip-v4",
        "networking": "lan",
        "piggyback": "auto-piggyback",
        "site": "unit",
        "snmp_ds": "no-snmp",
    }
    assert config_cache.tags_of_host(test_host) == cfg.tag_groups


def test_service_tag_rules_default() -> None:
    assert isinstance(config.service_tag_rules, list)


def test_tags_of_service(monkeypatch: MonkeyPatch) -> None:
    test_host = HostName("test-host")
    xyz_host = HostName("xyz")

    ts = Scenario()
    ts.add_host(test_host, tags={"agent": "no-agent"})
    ts.add_host(xyz_host)
    ts.set_ruleset(
        "service_tag_rules",
        [
            ([("criticality", "prod")], ["no-agent"], config.ALL_HOSTS, ["CPU load$"], {}),
        ],
    )

    config_cache = ts.apply(monkeypatch)

    cfg = config_cache.get_host_config(xyz_host)
    assert cfg.tag_groups == {
        "address_family": "ip-v4-only",
        "agent": "cmk-agent",
        "criticality": "prod",
        "ip-v4": "ip-v4",
        "networking": "lan",
        "piggyback": "auto-piggyback",
        "site": "unit",
        "snmp_ds": "no-snmp",
        "tcp": "tcp",
        "checkmk-agent": "checkmk-agent",
    }
    assert config_cache.tags_of_service(xyz_host, "CPU load") == {}

    cfg = config_cache.get_host_config(test_host)
    assert cfg.tag_groups == {
        "address_family": "ip-v4-only",
        "agent": "no-agent",
        "criticality": "prod",
        "ip-v4": "ip-v4",
        "networking": "lan",
        "piggyback": "auto-piggyback",
        "site": "unit",
        "snmp_ds": "no-snmp",
    }
    assert config_cache.tags_of_service(test_host, "CPU load") == {"criticality": "prod"}


def test_host_label_rules_default() -> None:
    assert isinstance(config.host_label_rules, list)


def test_host_config_labels(monkeypatch: MonkeyPatch) -> None:
    test_host = HostName("test-host")
    xyz_host = HostName("xyz")

    ts = Scenario()
    ts.set_ruleset(
        "host_label_rules",
        [
            ({"from-rule": "rule1"}, ["no-agent"], config.ALL_HOSTS, {}),
            ({"from-rule2": "rule2"}, ["no-agent"], config.ALL_HOSTS, {}),
        ],
    )

    ts.add_host(test_host, tags={"agent": "no-agent"}, labels={"explicit": "ding"})
    ts.add_host(xyz_host)
    config_cache = ts.apply(monkeypatch)

    cfg = config_cache.get_host_config(xyz_host)
    assert cfg.labels == {"cmk/site": "NO_SITE"}

    cfg = config_cache.get_host_config(test_host)
    assert cfg.labels == {
        "cmk/site": "NO_SITE",
        "explicit": "ding",
        "from-rule": "rule1",
        "from-rule2": "rule2",
    }
    assert cfg.label_sources == {
        "cmk/site": "discovered",
        "explicit": "explicit",
        "from-rule": "ruleset",
        "from-rule2": "ruleset",
    }


def test_host_labels_of_host_discovered_labels(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    test_host = HostName("test-host")
    ts = Scenario()
    ts.add_host(test_host)

    monkeypatch.setattr(cmk.utils.paths, "discovered_host_labels_dir", tmp_path)
    host_file = (tmp_path / test_host).with_suffix(".mk")
    with host_file.open(mode="w", encoding="utf-8") as f:
        f.write(repr({"äzzzz": {"value": "eeeeez", "plugin_name": "ding123"}}) + "\n")

    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(test_host).labels == {
        "cmk/site": "NO_SITE",
        "äzzzz": "eeeeez",
    }
    assert config_cache.get_host_config(test_host).label_sources == {
        "cmk/site": "discovered",
        "äzzzz": "discovered",
    }


def test_service_label_rules_default() -> None:
    assert isinstance(config.service_label_rules, list)


def test_labels_of_service(monkeypatch: MonkeyPatch) -> None:
    test_host = HostName("test-host")
    xyz_host = HostName("xyz")
    ts = Scenario()
    ts.set_ruleset(
        "service_label_rules",
        [
            ({"label1": "val1"}, ["no-agent"], config.ALL_HOSTS, ["CPU load$"], {}),
            ({"label2": "val2"}, ["no-agent"], config.ALL_HOSTS, ["CPU load$"], {}),
        ],
    )

    ts.add_host(test_host, tags={"agent": "no-agent"})
    config_cache = ts.apply(monkeypatch)

    assert config_cache.labels_of_service(xyz_host, "CPU load") == {}
    assert config_cache.label_sources_of_service(xyz_host, "CPU load") == {}

    assert config_cache.labels_of_service(test_host, "CPU load") == {
        "label1": "val1",
        "label2": "val2",
    }
    assert config_cache.label_sources_of_service(test_host, "CPU load") == {
        "label1": "ruleset",
        "label2": "ruleset",
    }


@pytest.mark.usefixtures("fix_register")
def test_labels_of_service_discovered_labels(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    test_host = HostName("test-host")
    xyz_host = HostName("xyz")
    ts = Scenario()
    ts.add_host(test_host)

    monkeypatch.setattr(cmk.utils.paths, "autochecks_dir", str(tmp_path))
    autochecks_file = Path(cmk.utils.paths.autochecks_dir, "test-host.mk")
    with autochecks_file.open("w", encoding="utf-8") as f:
        f.write(
            """[
    {'check_plugin_name': 'cpu_loads', 'item': None, 'parameters': (5.0, 10.0), 'service_labels': {u'äzzzz': u'eeeeez'}},
]"""
        )

    config_cache = ts.apply(monkeypatch)

    service = config_cache.get_autochecks_of(test_host)[0]
    assert service.description == "CPU load"

    assert config_cache.labels_of_service(xyz_host, "CPU load") == {}
    assert config_cache.label_sources_of_service(xyz_host, "CPU load") == {}

    assert config_cache.labels_of_service(test_host, service.description) == {"äzzzz": "eeeeez"}
    assert config_cache.label_sources_of_service(test_host, service.description) == {
        "äzzzz": "discovered"
    }


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", {"check_interval": 1.0}),
        (
            "testhost2",
            {
                "_CUSTOM": ["value1"],
                "dingdong": ["value1"],
                "check_interval": 10.0,
            },
        ),
    ],
)
def test_config_cache_extra_attributes_of_service(
    monkeypatch: MonkeyPatch, hostname_str: str, result: Dict[str, Any]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option(
        "extra_service_conf",
        {
            "check_interval": [
                ("10", [], ["testhost2"], "CPU load$", {}),
            ],
            "dingdong": [
                (
                    [
                        "value1",
                    ],
                    [],
                    ["testhost2"],
                    "CPU load$",
                    {},
                ),
                (
                    [
                        "value2",
                    ],
                    [],
                    ["testhost2"],
                    "CPU load$",
                    {},
                ),
            ],
            "_custom": [
                (
                    [
                        "value1",
                    ],
                    [],
                    ["testhost2"],
                    "CPU load$",
                    {},
                ),
                (
                    [
                        "value2",
                    ],
                    [],
                    ["testhost2"],
                    "CPU load$",
                    {},
                ),
            ],
        },
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.extra_attributes_of_service(hostname, "CPU load") == result


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", []),
        ("testhost2", ["icon1", "icon2"]),
    ],
)
def test_config_cache_icons_and_actions(
    monkeypatch: MonkeyPatch, hostname_str: str, result: List[str]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "service_icons_and_actions",
        [
            ("icon1", [], ["testhost2"], "CPU load$", {}),
            ("icon1", [], ["testhost2"], "CPU load$", {}),
            ("icon2", [], ["testhost2"], "CPU load$", {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert sorted(
        config_cache.icons_and_actions_of_service(
            hostname,
            "CPU load",
            CheckPluginName("ps"),
            {},
        )
    ) == sorted(result)


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", []),
        ("testhost2", ["dingdong"]),
    ],
)
def test_config_cache_servicegroups_of_service(
    monkeypatch: MonkeyPatch, hostname_str: str, result: List[str]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "service_groups",
        [
            ("dingdong", [], ["testhost2"], "CPU load$", {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.servicegroups_of_service(hostname, "CPU load") == result


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        # No rule matches for this host
        ("testhost1", []),
        # Take the group from the ruleset (dingdong) and the definition from the nearest folder in
        # the hierarchy (abc). Don't apply the definition from the parent folder (xyz).
        ("testhost2", ["abc", "dingdong"]),
        # Take the group from all rulesets (dingdong, haha) and the definition from the nearest
        # folder in the hierarchy (abc). Don't apply the definition from the parent folder (xyz).
        ("testhost3", ["abc", "dingdong", "haha"]),
    ],
)
def test_config_cache_contactgroups_of_service(
    monkeypatch: MonkeyPatch, hostname_str: str, result: List[str]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
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
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert sorted(config_cache.contactgroups_of_service(hostname, "CPU load")) == sorted(result)


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", "24X7"),
        ("testhost2", "workhours"),
    ],
)
def test_config_cache_passive_check_period_of_service(
    monkeypatch: MonkeyPatch, hostname_str: str, result: str
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "check_periods",
        [
            ("workhours", [], ["testhost2"], ["CPU load$"], {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.passive_check_period_of_service(hostname, "CPU load") == result


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", {}),
        (
            "testhost2",
            {
                "ATTR1": "value1",
                "ATTR2": "value2",
            },
        ),
    ],
)
def test_config_cache_custom_attributes_of_service(
    monkeypatch: MonkeyPatch, hostname_str: str, result: Dict[str, str]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "custom_service_attributes",
        [
            (
                [
                    ("ATTR1", "value1"),
                    ("ATTR2", "value2"),
                ],
                [],
                ["testhost2"],
                ["CPU load$"],
                {},
            ),
            (
                [
                    ("ATTR1", "value1"),
                ],
                [],
                ["testhost2"],
                ["CPU load$"],
                {},
            ),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.custom_attributes_of_service(hostname, "CPU load") == result


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", None),
        ("testhost2", 10),
    ],
)
def test_config_cache_service_level_of_service(
    monkeypatch: MonkeyPatch, hostname_str: str, result: Optional[int]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "service_service_levels",
        [
            (10, [], ["testhost2"], ["CPU load$"], {}),
            (2, [], ["testhost2"], ["CPU load$"], {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.service_level_of_service(hostname, "CPU load") == result


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", None),
        ("testhost2", None),
        ("testhost3", "xyz"),
    ],
)
def test_config_cache_check_period_of_service(
    monkeypatch: MonkeyPatch, hostname_str: str, result: Optional[str]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
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


@pytest.mark.parametrize(
    "edition,expected_cache_class_name,expected_host_class_name",
    [
        (cmk_version.Edition.CME, "CEEConfigCache", "CEEHostConfig"),
        (cmk_version.Edition.CEE, "CEEConfigCache", "CEEHostConfig"),
        (cmk_version.Edition.CRE, "ConfigCache", "HostConfig"),
    ],
)
def test_config_cache_get_host_config(
    monkeypatch: MonkeyPatch,
    edition: cmk_version.Edition,
    expected_cache_class_name: str,
    expected_host_class_name: str,
) -> None:
    monkeypatch.setattr(cmk_version, "is_raw_edition", lambda: edition is cmk_version.Edition.CRE)

    _config_cache.clear()

    xyz_host = HostName("xyz")

    ts = Scenario()
    ts.add_host(xyz_host)
    cache = ts.apply(monkeypatch)

    assert cache.__class__.__name__ == expected_cache_class_name

    host_config = cache.get_host_config(xyz_host)
    assert host_config.__class__.__name__ == expected_host_class_name
    assert isinstance(host_config, config.HostConfig)
    assert host_config is cache.get_host_config(xyz_host)


def test_host_config_max_cachefile_age_no_cluster(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    xyz_host = HostName("xyz")
    ts.add_host(xyz_host)
    ts.apply(monkeypatch)

    host_config = config.HostConfig.make_host_config(xyz_host)
    assert not host_config.is_cluster
    assert host_config.max_cachefile_age.get(Mode.CHECKING) == config.check_max_cachefile_age
    assert host_config.max_cachefile_age.get(Mode.CHECKING) != config.cluster_max_cachefile_age


def test_host_config_max_cachefile_age_cluster(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    clu = HostName("clu")
    ts.add_cluster(clu)
    ts.apply(monkeypatch)

    host_config = config.HostConfig.make_host_config(clu)
    assert host_config.is_cluster
    assert host_config.max_cachefile_age.get(Mode.CHECKING) != config.check_max_cachefile_age
    assert host_config.max_cachefile_age.get(Mode.CHECKING) == config.cluster_max_cachefile_age


@pytest.mark.parametrize(
    "use_new_descr,result",
    [
        (True, "Check_MK Discovery"),
        (False, "Check_MK inventory"),
    ],
)
def test_config_cache_service_discovery_name(
    monkeypatch: MonkeyPatch, use_new_descr: bool, result: str
) -> None:
    ts = Scenario()
    if use_new_descr:
        ts.set_option("use_new_descriptions_for", ["cmk_inventory"])
    config_cache = ts.apply(monkeypatch)

    assert config_cache.service_discovery_name() == result


def test_config_cache_get_clustered_service_node_keys_no_cluster(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()

    config_cache = ts.apply(monkeypatch)

    monkeypatch.setattr(
        config,
        "lookup_ip_address",
        lambda host_config, *, family=None: "dummy.test.ip.0",
    )
    # empty, we have no cluster:
    assert [] == config_cache.get_clustered_service_node_keys(
        config_cache.get_host_config(HostName("cluster.test")),
        SourceType.HOST,
        "Test Service",
    )


def test_config_cache_get_clustered_service_node_keys_cluster_no_service(
    monkeypatch: MonkeyPatch,
) -> None:
    cluster_test = HostName("cluster.test")
    ts = Scenario()
    ts.add_cluster(cluster_test, nodes=["node1.test", "node2.test"])
    config_cache = ts.apply(monkeypatch)

    monkeypatch.setattr(
        config,
        "lookup_ip_address",
        lambda host_config, *, family=None: "dummy.test.ip.0",
    )
    # empty for a node:
    assert [] == config_cache.get_clustered_service_node_keys(
        config_cache.get_host_config(HostName("node1.test")),
        SourceType.HOST,
        "Test Service",
    )

    # empty for cluster (we have not clustered the service)
    assert [] == config_cache.get_clustered_service_node_keys(
        config_cache.get_host_config(cluster_test),
        SourceType.HOST,
        "Test Service",
    )


def test_config_cache_get_clustered_service_node_keys_clustered(monkeypatch: MonkeyPatch) -> None:
    node1 = HostName("node1.test")
    node2 = HostName("node2.test")
    cluster = HostName("cluster.test")

    ts = Scenario()
    ts.add_host(node1)
    ts.add_host(node2)
    ts.add_cluster(cluster, nodes=["node1.test", "node2.test"])
    # add a fake rule, that defines a cluster
    ts.set_option(
        "clustered_services_mapping",
        [
            {
                "value": "cluster.test",
                "condition": {"service_description": ["Test Service"]},
            }
        ],
    )
    config_cache = ts.apply(monkeypatch)

    monkeypatch.setattr(
        config,
        "lookup_ip_address",
        lambda host_config, *, family=None: "dummy.test.ip.%s" % host_config.hostname[4],
    )
    assert config_cache.get_clustered_service_node_keys(
        config_cache.get_host_config(cluster),
        SourceType.HOST,
        "Test Service",
    ) == [
        HostKey(node1, "dummy.test.ip.1", SourceType.HOST),
        HostKey(node2, "dummy.test.ip.2", SourceType.HOST),
    ]
    monkeypatch.setattr(
        config,
        "lookup_ip_address",
        lambda host_config, *, family=None: "dummy.test.ip.0",
    )
    assert [] == config_cache.get_clustered_service_node_keys(
        config_cache.get_host_config(cluster),
        SourceType.HOST,
        "Test Unclustered",
    )


def test_host_ruleset_match_object_of_service(monkeypatch: MonkeyPatch) -> None:
    test_host = HostName("test-host")
    xyz_host = HostName("xyz")

    ts = Scenario()
    ts.add_host(xyz_host)
    ts.add_host(test_host, tags={"agent": "no-agent"})
    ts.set_autochecks(
        test_host,
        [
            AutocheckEntry(
                CheckPluginName("cpu_load"),
                None,
                {},
                {"abc": "xä"},
            )
        ],
    )
    config_cache = ts.apply(monkeypatch)

    obj = config_cache.ruleset_match_object_of_service(xyz_host, "bla blä")
    assert isinstance(obj, RulesetMatchObject)
    assert obj.to_dict() == {
        "host_name": "xyz",
        "service_description": "bla blä",
        "service_labels": {},
        "service_cache_id": ("bla blä", hash(frozenset([]))),
    }

    # Funny service description because the plugin isn't loaded.
    # We could patch config.service_description, but this is easier:
    description = "Unimplemented check cpu_load"

    obj = config_cache.ruleset_match_object_of_service(test_host, description)
    service_labels = {"abc": "xä"}
    assert isinstance(obj, RulesetMatchObject)
    assert obj.to_dict() == {
        "host_name": "test-host",
        "service_description": description,
        "service_labels": service_labels,
        "service_cache_id": (description, hash(frozenset(service_labels.items()))),
    }


@pytest.mark.parametrize(
    "result,ruleset",
    [
        (False, None),
        (False, []),
        (False, [(None, [], config.ALL_HOSTS, {})]),
        (False, [({}, [], config.ALL_HOSTS, {})]),
        (True, [({"status_data_inventory": True}, [], config.ALL_HOSTS, {})]),
        (False, [({"status_data_inventory": False}, [], config.ALL_HOSTS, {})]),
    ],
)
def test_host_config_do_status_data_inventory(
    monkeypatch: MonkeyPatch, result: bool, ruleset: Optional[List[Tuple]]
) -> None:
    abc_host = HostName("abc")
    ts = Scenario()
    ts.add_host(abc_host)
    ts.set_option(
        "active_checks",
        {
            "cmk_inv": ruleset,
        },
    )
    config_cache = ts.apply(monkeypatch)

    assert config_cache.get_host_config(abc_host).do_status_data_inventory == result


@pytest.mark.parametrize(
    "hostname_str,result",
    [
        ("testhost1", None),
        ("testhost2", 10),
    ],
)
def test_host_config_service_level(
    monkeypatch: MonkeyPatch, hostname_str: str, result: Optional[int]
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "host_service_levels",
        [
            (10, [], ["testhost2"], {}),
            (2, [], ["testhost2"], {}),
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config(hostname).service_level == result


def _rule_val(check_interval: Optional[int]) -> dict[str, Any]:
    return {
        "check_interval": check_interval,
        "severity_unmonitored": 0,
        "severity_vanished": 0,
        "severity_new_host_label": 0,
    }


@pytest.mark.parametrize(
    "rule_entries,ignored,ping,result",
    [
        ([None], False, False, False),
        ([], False, False, True),
        ([_rule_val(None)], False, False, False),
        ([_rule_val(0)], False, False, False),
        ([_rule_val(3600)], False, False, True),
        ([_rule_val(3600)], True, False, False),
        ([_rule_val(3600)], False, True, False),
    ],
)
def test_host_config_add_discovery_check(
    monkeypatch: MonkeyPatch,
    rule_entries: Sequence[Optional[dict]],
    ignored: bool,
    ping: bool,
    result: bool,
) -> None:
    xyz_host = HostName("xyz")
    if ping:
        tags = {
            "agent": "no-agent",
            "snmp_ds": "no-snmp",
            "piggyback": "no-piggyback",
        }
    else:
        tags = {}

    ts = Scenario()
    ts.add_host(xyz_host, tags=tags)

    ts.set_ruleset(
        "periodic_discovery",
        [
            {
                "condition": {
                    "host_name": ["xyz"],
                },
                "value": value,
            }
            for value in rule_entries
        ],
    )

    if ignored:
        ts.set_ruleset(
            "ignored_services",
            [
                {
                    "condition": {
                        "service_description": [{"$regex": "Check_MK Discovery"}],
                        "host_name": ["xyz"],
                    },
                    "value": True,
                },
            ],
        )
    config_cache = ts.apply(monkeypatch)

    monkeypatch.setattr(config, "inventory_check_interval", 42)

    host_config = config_cache.get_host_config(xyz_host)
    params = host_config.discovery_check_parameters

    assert host_config.add_service_discovery_check(params, "Check_MK Discovery") == result


def test_get_config_file_paths_with_confd(folder_path_test_config: None) -> None:
    rel_paths = [
        "%s" % p.relative_to(cmk.utils.paths.default_config_dir)
        for p in config.get_config_file_paths(with_conf_d=True)
    ]
    assert rel_paths == [
        "main.mk",
        "conf.d/wato/hosts.mk",
        "conf.d/wato/rules.mk",
        "conf.d/wato/lvl1/hosts.mk",
        "conf.d/wato/lvl1/rules.mk",
        "conf.d/wato/lvl1/lvl2/hosts.mk",
        "conf.d/wato/lvl1/lvl2/rules.mk",
        "conf.d/wato/lvl1_aaa/hosts.mk",
        "conf.d/wato/lvl1_aaa/rules.mk",
    ]


def test_load_config_folder_paths(folder_path_test_config: None) -> None:
    assert config.host_paths == {
        "lvl1-host": "/wato/lvl1/hosts.mk",
        "lvl1aaa-host": "/wato/lvl1_aaa/hosts.mk",
        "lvl2-host": "/wato/lvl1/lvl2/hosts.mk",
        "lvl0-host": "/wato/hosts.mk",
    }

    config_cache = config.get_config_cache()

    assert config_cache.host_path(HostName("main-host")) == "/"
    assert config_cache.host_path(HostName("lvl0-host")) == "/wato/"
    assert config_cache.host_path(HostName("lvl1-host")) == "/wato/lvl1/"
    assert config_cache.host_path(HostName("lvl1aaa-host")) == "/wato/lvl1_aaa/"
    assert config_cache.host_path(HostName("lvl2-host")) == "/wato/lvl1/lvl2/"

    assert config.cmc_host_rrd_config[0]["condition"]["host_folder"] == "/wato/lvl1_aaa/"
    assert config.cmc_host_rrd_config[1]["condition"]["host_folder"] == "/wato/lvl1/lvl2/"
    assert config.cmc_host_rrd_config[2]["condition"]["host_folder"] == "/wato/lvl1/"
    assert "host_folder" not in config.cmc_host_rrd_config[3]["condition"]
    assert "host_folder" not in config.cmc_host_rrd_config[4]["condition"]

    assert config_cache.host_extra_conf(HostName("main-host"), config.cmc_host_rrd_config) == [
        "LVL0",
        "MAIN",
    ]
    assert config_cache.host_extra_conf(HostName("lvl0-host"), config.cmc_host_rrd_config) == [
        "LVL0",
        "MAIN",
    ]
    assert config_cache.host_extra_conf(HostName("lvl1-host"), config.cmc_host_rrd_config) == [
        "LVL1",
        "LVL0",
        "MAIN",
    ]
    assert config_cache.host_extra_conf(HostName("lvl1aaa-host"), config.cmc_host_rrd_config) == [
        "LVL1aaa",
        "LVL0",
        "MAIN",
    ]
    assert config_cache.host_extra_conf(HostName("lvl2-host"), config.cmc_host_rrd_config) == [
        "LVL2",
        "LVL1",
        "LVL0",
        "MAIN",
    ]


@pytest.fixture(name="folder_path_test_config")
def folder_path_test_config_fixture(monkeypatch: MonkeyPatch) -> Generator[None, None, None]:
    config_dir = Path(cmk.utils.paths.check_mk_config_dir)
    config_dir.mkdir(parents=True, exist_ok=True)

    with Path(cmk.utils.paths.main_config_file).open("w", encoding="utf-8") as f:
        f.write(
            """
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

"""
            % {"name": "main-host"}
        )

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


def _add_host_in_folder(folder_path: Path, name: str) -> None:
    with (folder_path / "hosts.mk").open("w", encoding="utf-8") as f:
        f.write(
            """
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
"""
            % {"name": name}
        )


def _add_rule_in_folder(folder_path: Path, value: str) -> None:
    with (folder_path / "rules.mk").open("w", encoding="utf-8") as f:
        if value == "LVL0":
            condition = "{}"
        else:
            condition = "{'host_folder': '/%s/' % FOLDER_PATH}"

        f.write(
            """
cmc_host_rrd_config = [
{'condition': %s, 'value': '%s'},
] + cmc_host_rrd_config
"""
            % (condition, value)
        )


def _add_explicit_setting_in_folder(
    folder_path: Path, setting_name: str, values: Dict[str, Any]
) -> None:
    folder_path.mkdir(parents=True, exist_ok=True)
    with (folder_path / "hosts.mk").open("w", encoding="utf-8") as f:
        f.write(
            f"""
# Explicit settings for {setting_name}
explicit_host_conf.setdefault('{setting_name}', {{}})
explicit_host_conf['{setting_name}'].update({values})
"""
        )


def test_explicit_setting_loading():
    main_mk_file = Path(cmk.utils.paths.main_config_file)
    settings = [
        ("sub1", "parents", {"hostA": "setting1"}),
        ("sub2", "parents", {"hostB": "setting2"}),
        ("sub3", "other", {"hostA": "setting3"}),
        ("sub4", "other", {"hostB": "setting4"}),
    ]
    config_dir = Path(cmk.utils.paths.check_mk_config_dir)
    wato_main_folder = config_dir / "wato"
    try:
        main_mk_file.touch()
        for foldername, setting, values in settings:
            _add_explicit_setting_in_folder(wato_main_folder / foldername, setting, values)

        config.load()
        assert config.explicit_host_conf["parents"]["hostA"] == "setting1"
        assert config.explicit_host_conf["parents"]["hostB"] == "setting2"
        assert config.explicit_host_conf["other"]["hostA"] == "setting3"
        assert config.explicit_host_conf["other"]["hostB"] == "setting4"
    finally:
        main_mk_file.unlink()
        for foldername, _setting, _values in settings:
            shutil.rmtree(wato_main_folder / foldername, ignore_errors=True)


@pytest.fixture(name="config_path")
def fixture_config_path() -> VersionedConfigPath:
    return VersionedConfigPath(13)


def test_save_packed_config(monkeypatch: MonkeyPatch, config_path: VersionedConfigPath) -> None:
    ts = Scenario()
    ts.add_host(HostName("bla1"))
    config_cache = ts.apply(monkeypatch)
    precompiled_check_config = Path(config_path) / "precompiled_check_config.mk"

    assert not precompiled_check_config.exists()

    config.save_packed_config(config_path, config_cache)

    assert precompiled_check_config.exists()


def test_load_packed_config(config_path: VersionedConfigPath) -> None:
    config.PackedConfigStore.from_serial(config_path).write({"abc": 1})

    assert "abc" not in config.__dict__
    config.load_packed_config(config_path)
    # Mypy does not understand that we add some new member for testing
    assert config.abc == 1  # type: ignore[attr-defined]
    del config.__dict__["abc"]


class TestPackedConfigStore:
    @pytest.fixture()
    def store(self, config_path: VersionedConfigPath) -> config.PackedConfigStore:
        return config.PackedConfigStore.from_serial(config_path)

    def test_read_not_existing_file(self, store: config.PackedConfigStore) -> None:
        with pytest.raises(FileNotFoundError):
            store.read()

    def test_write(self, store: config.PackedConfigStore, config_path: VersionedConfigPath) -> None:
        precompiled_check_config = Path(config_path) / "precompiled_check_config.mk"
        assert not precompiled_check_config.exists()

        store.write({"abc": 1})

        assert precompiled_check_config.exists()
        assert store.read() == {"abc": 1}


def test__extract_check_plugins(monkeypatch: MonkeyPatch) -> None:
    duplicate_plugin = {
        "duplicate_plugin": {
            "service_description": "blah",
        },
    }
    registered_plugin = CheckPlugin(
        CheckPluginName("duplicate_plugin"),
        [],
        "Duplicate Plugin",
        lambda: [],
        None,
        None,
        "merged",
        lambda: [],
        None,
        None,
        None,
        None,
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


def test__extract_agent_and_snmp_sections(monkeypatch: MonkeyPatch) -> None:
    duplicate_plugin: dict[str, dict[str, Any]] = {
        "duplicate_plugin": {},
    }
    registered_section = SNMPSectionPlugin(
        SectionName("duplicate_plugin"),
        ParsedSectionName("duplicate_plugin"),
        lambda x: None,
        lambda: (HostLabel(x, "bar") for x in ["foo"]),
        None,
        None,
        "merged",
        [],
        [],
        set(),
        None,
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
    assert (
        agent_based_register.get_section_plugin(SectionName("duplicate_plugin"))
        == registered_section
    )
