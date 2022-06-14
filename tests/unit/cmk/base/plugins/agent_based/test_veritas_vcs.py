#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import veritas_vcs
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state
from cmk.base.plugins.agent_based.veritas_vcs import Vcs

STRING_TABLE = [
    ["ClusState", "RUNNING"],
    ["ClusterName", "minions"],
    ["#System", "Attribute", "Value"],
    ["dave", "SysState", "RUNNING"],
    ["stuart", "SysState", "RUNNING"],
    ["#Group", "Attribute", "System", "Value"],
    ["ClusterService", "State", "stuart", "|OFFLINE|"],
    ["bob1", "State", "stuart", "|OFFLINE|"],
    ["bob2", "State", "stuart", "|OFFLINE|"],
    ["bob3", "State", "stuart", "|OFFLINE|"],
    ["bob4", "State", "stuart", "|OFFLINE|"],
    ["bob5", "State", "stuart", "|OFFLINE|"],
    ["agnes", "State", "stuart", "|ONLINE|"],
    ["#Resource", "Attribute", "System", "Value"],
    ["gru", "State", "stuart", "ONLINE"],
    ["bob1-db", "State", "stuart", "OFFLINE"],
    ["bob1-dg", "State", "stuart", "OFFLINE"],
    ["bob1-ip", "State", "stuart", "OFFLINE"],
    ["bob1-mnt", "State", "stuart", "OFFLINE"],
    ["bob1-nic-proxy", "State", "stuart", "ONLINE"],
    ["bob1-vol", "State", "stuart", "OFFLINE"],
    ["bob2-db", "State", "stuart", "OFFLINE"],
    ["bob2-dg", "State", "stuart", "OFFLINE"],
    ["bob2-ip", "State", "stuart", "OFFLINE"],
    ["bob2-mnt", "State", "stuart", "OFFLINE"],
    ["bob2-nic-proxy", "State", "stuart", "ONLINE"],
    ["bob2-vol", "State", "stuart", "OFFLINE"],
    ["bob3-db", "State", "stuart", "OFFLINE"],
    ["bob3-dg", "State", "stuart", "OFFLINE"],
    ["bob3-ip", "State", "stuart", "OFFLINE"],
    ["bob3-mnt", "State", "stuart", "OFFLINE"],
    ["bob3-nic-proxy", "State", "stuart", "ONLINE"],
    ["bob3-vol", "State", "stuart", "OFFLINE"],
    ["bob4-db", "State", "stuart", "OFFLINE"],
    ["bob4-dg", "State", "stuart", "OFFLINE"],
    ["bob4-ip", "State", "stuart", "OFFLINE"],
    ["bob4-mnt", "State", "stuart", "OFFLINE"],
    ["bob4-nic-proxy", "State", "stuart", "ONLINE"],
    ["bob4-vol", "State", "stuart", "OFFLINE"],
    ["bob5-db", "State", "stuart", "OFFLINE"],
    ["bob5-dg", "State", "stuart", "OFFLINE"],
    ["bob5-ip", "State", "stuart", "OFFLINE"],
    ["bob5-mnt", "State", "stuart", "OFFLINE"],
    ["bob5-nic-proxy", "State", "stuart", "ONLINE"],
    ["bob5-vol", "State", "stuart", "OFFLINE"],
    ["agnes-nic", "State", "stuart", "ONLINE"],
    ["agnes-phantom", "State", "stuart", "ONLINE"],
    ["webip", "State", "stuart", "OFFLINE"],
]

SECTION: veritas_vcs.Section = {
    "resource": {
        "bob3-nic-proxy": [Vcs(attr="State", value="ONLINE", cluster="minions")],
        "bob3-dg": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob1-db": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob3-db": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob1-dg": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob2-vol": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob2-nic-proxy": [Vcs(attr="State", value="ONLINE", cluster="minions")],
        "bob5-ip": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob1-nic-proxy": [Vcs(attr="State", value="ONLINE", cluster="minions")],
        "webip": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob5-vol": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob2-dg": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "gru": [Vcs(attr="State", value="ONLINE", cluster="minions")],
        "bob2-db": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "agnes-phantom": [Vcs(attr="State", value="ONLINE", cluster="minions")],
        "bob1-vol": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob4-vol": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob4-mnt": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob4-db": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob4-dg": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "agnes-nic": [Vcs(attr="State", value="ONLINE", cluster="minions")],
        "bob3-mnt": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob5-db": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob3-vol": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob5-nic-proxy": [Vcs(attr="State", value="ONLINE", cluster="minions")],
        "bob1-mnt": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob4-ip": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob5-mnt": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob3-ip": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob5-dg": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob2-mnt": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob2-ip": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob4-nic-proxy": [Vcs(attr="State", value="ONLINE", cluster="minions")],
        "bob1-ip": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
    },
    "cluster": {"minions": [Vcs(attr="ClusState", value="RUNNING", cluster=None)]},
    "group": {
        "bob2": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob5": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob4": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob3": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "ClusterService": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "bob1": [Vcs(attr="State", value="OFFLINE", cluster="minions")],
        "agnes": [Vcs(attr="State", value="ONLINE", cluster="minions")],
    },
    "system": {
        "dave": [Vcs(attr="SysState", value="RUNNING", cluster="minions")],
        "stuart": [Vcs(attr="SysState", value="RUNNING", cluster="minions")],
    },
}


def test_parse_veritas_vcs() -> None:
    assert veritas_vcs.parse_veritas_vcs(STRING_TABLE) == SECTION


STRING_TABLE_HASHES = [
    ["ClusState", "RUNNING"],
    ["ClusterName", "c7dbacpt"],
    ["#System", "Attribute", "Value"],
    ["dave", "SysState", "RUNNING"],
    ["stuart", "SysState", "RUNNING"],
    ["#Group", "Attribute", "System", "Value"],
    ["ClusterService", "State", "stuart", "|OFFLINE|"],
    ["nepharius", "State", "stuart", "|ONLINE|"],
    ["lan", "State", "stuart", "|ONLINE|"],
    ["omd", "State", "stuart", "|ONLINE|"],
    ["#Resource", "Attribute", "System", "Value"],
    ["nepharius_mrs", "State", "stuart", "ONLINE"],
    ["nepharius_dr", "State", "stuart", "ONLINE"],
    ["cs_ip", "State", "stuart", "OFFLINE"],
    ["cs_proxy", "State", "stuart", "ONLINE"],
    ["lan_nic", "State", "stuart", "ONLINE"],
    ["lan_phantom", "State", "stuart", "ONLINE"],
    ["omd_apache", "State", "stuart", "ONLINE"],
    ["omd_appl", "State", "stuart", "ONLINE"],
    ["omd_dg", "State", "stuart", "ONLINE"],
    ["omd_proxy", "State", "stuart", "ONLINE"],
    ["omd_srdf", "State", "stuart", "ONLINE"],
    ["omd_uc4ps1_agt", "State", "stuart", "ONLINE"],
    ["omdp_ip", "State", "stuart", "ONLINE"],
    ["omdp_mnt", "State", "stuart", "ONLINE"],
    ["#Group", "Attribute", "System", "Value"],
    ["ClusterService", "Frozen", "global", "0"],
    ["ClusterService", "TFrozen", "global", "0"],
    ["#"],
    ["nepharius", "Frozen", "global", "0"],
    ["nepharius", "TFrozen", "global", "1"],
    ["#"],
    ["lan", "Frozen", "global", "0"],
    ["lan", "TFrozen", "global", "0"],
    ["#"],
    ["omd", "Frozen", "global", "1"],
    ["omd", "TFrozen", "global", "0"],
]

SECTION_HASHES: veritas_vcs.Section = {
    "resource": {
        "lan_phantom": [Vcs(attr="State", value="ONLINE", cluster="c7dbacpt")],
        "omdp_mnt": [Vcs(attr="State", value="ONLINE", cluster="c7dbacpt")],
        "nepharius_mrs": [Vcs(attr="State", value="ONLINE", cluster="c7dbacpt")],
        "omd_uc4ps1_agt": [Vcs(attr="State", value="ONLINE", cluster="c7dbacpt")],
        "omd_appl": [Vcs(attr="State", value="ONLINE", cluster="c7dbacpt")],
        "omd_srdf": [Vcs(attr="State", value="ONLINE", cluster="c7dbacpt")],
        "omd_apache": [Vcs(attr="State", value="ONLINE", cluster="c7dbacpt")],
        "omdp_ip": [Vcs(attr="State", value="ONLINE", cluster="c7dbacpt")],
        "lan_nic": [Vcs(attr="State", value="ONLINE", cluster="c7dbacpt")],
        "omd_dg": [Vcs(attr="State", value="ONLINE", cluster="c7dbacpt")],
        "cs_proxy": [Vcs(attr="State", value="ONLINE", cluster="c7dbacpt")],
        "nepharius_dr": [Vcs(attr="State", value="ONLINE", cluster="c7dbacpt")],
        "cs_ip": [Vcs(attr="State", value="OFFLINE", cluster="c7dbacpt")],
        "omd_proxy": [Vcs(attr="State", value="ONLINE", cluster="c7dbacpt")],
    },
    "cluster": {"c7dbacpt": [Vcs(attr="ClusState", value="RUNNING", cluster=None)]},
    "group": {
        "lan": [
            Vcs(attr="State", value="ONLINE", cluster="c7dbacpt"),
            Vcs(attr="Frozen", value="0", cluster="c7dbacpt"),
            Vcs(attr="TFrozen", value="0", cluster="c7dbacpt"),
        ],
        "ClusterService": [
            Vcs(attr="State", value="OFFLINE", cluster="c7dbacpt"),
            Vcs(attr="Frozen", value="0", cluster="c7dbacpt"),
            Vcs(attr="TFrozen", value="0", cluster="c7dbacpt"),
        ],
        "nepharius": [
            Vcs(attr="State", value="ONLINE", cluster="c7dbacpt"),
            Vcs(attr="Frozen", value="0", cluster="c7dbacpt"),
            Vcs(attr="TFrozen", value="1", cluster="c7dbacpt"),
        ],
        "omd": [
            Vcs(attr="State", value="ONLINE", cluster="c7dbacpt"),
            Vcs(attr="Frozen", value="1", cluster="c7dbacpt"),
            Vcs(attr="TFrozen", value="0", cluster="c7dbacpt"),
        ],
    },
    "system": {
        "dave": [Vcs(attr="SysState", value="RUNNING", cluster="c7dbacpt")],
        "stuart": [Vcs(attr="SysState", value="RUNNING", cluster="c7dbacpt")],
    },
}


def test_parse_veritas_vcs_hashes() -> None:
    assert veritas_vcs.parse_veritas_vcs(STRING_TABLE_HASHES) == SECTION_HASHES


def test_discover_veritas_vcs() -> None:
    assert list(veritas_vcs.discover_veritas_vcs(SECTION)) == [Service(item="minions")]


def test_discover_veritas_vcs_system() -> None:
    assert list(veritas_vcs.discover_veritas_vcs_system(SECTION)) == [
        Service(item="dave"),
        Service(item="stuart"),
    ]


def test_discover_veritas_vcs_group() -> None:
    assert list(veritas_vcs.discover_veritas_vcs_group(SECTION)) == [
        Service(item="bob2"),
        Service(item="bob5"),
        Service(item="bob4"),
        Service(item="bob3"),
        Service(item="ClusterService"),
        Service(item="bob1"),
        Service(item="agnes"),
    ]


def test_discover_veritas_vcs_resource() -> None:
    assert list(veritas_vcs.discover_veritas_vcs_resource(SECTION)) == [
        Service(item="bob3-nic-proxy"),
        Service(item="bob3-dg"),
        Service(item="bob1-db"),
        Service(item="bob3-db"),
        Service(item="bob1-dg"),
        Service(item="bob2-vol"),
        Service(item="bob2-nic-proxy"),
        Service(item="bob5-ip"),
        Service(item="bob1-nic-proxy"),
        Service(item="webip"),
        Service(item="bob5-vol"),
        Service(item="bob2-dg"),
        Service(item="gru"),
        Service(item="bob2-db"),
        Service(item="agnes-phantom"),
        Service(item="bob1-vol"),
        Service(item="bob4-vol"),
        Service(item="bob4-mnt"),
        Service(item="bob4-db"),
        Service(item="bob4-dg"),
        Service(item="agnes-nic"),
        Service(item="bob3-mnt"),
        Service(item="bob5-db"),
        Service(item="bob3-vol"),
        Service(item="bob5-nic-proxy"),
        Service(item="bob1-mnt"),
        Service(item="bob4-ip"),
        Service(item="bob5-mnt"),
        Service(item="bob3-ip"),
        Service(item="bob5-dg"),
        Service(item="bob2-mnt"),
        Service(item="bob2-ip"),
        Service(item="bob4-nic-proxy"),
        Service(item="bob1-ip"),
    ]


@pytest.mark.parametrize(
    "states, expected_state",
    [
        (
            ["a"],
            "a",
        ),
        (
            ["a", "b"],
            "default",
        ),
        (
            ["a", "b", "RUNNING", "ONLINE", "UNKNOWN", "FAULTED", "x", "y"],
            "FAULTED",
        ),
        (
            ["a", "b", "RUNNING", "ONLINE", "UNKNOWN", "x", "y"],
            "UNKNOWN",
        ),
        (
            ["a", "b", "RUNNING", "ONLINE", "x", "y"],
            "ONLINE",
        ),
        (
            ["a", "b", "RUNNING", "x", "y"],
            "RUNNING",
        ),
    ],
)
def test_veritas_vcs_boil_down_states_in_cluster(states, expected_state) -> None:
    assert veritas_vcs.veritas_vcs_boil_down_states_in_cluster(states) == expected_state


PARAMS = {
    "map_frozen": {"frozen": 2, "tfrozen": 1},
    "map_states": {
        "FAULTED": 2,
        "RUNNING": 0,
        "OK": 0,
        "ONLINE": 0,
        "default": 1,
        "PARTIAL": 1,
        "OFFLINE": 1,
        "UNKNOWN": 3,
        "EXITED": 1,
    },
}


def test_check_veritas_vcs() -> None:
    assert list(veritas_vcs.check_veritas_vcs("minions", PARAMS, SECTION)) == [
        Result(
            state=state.OK,
            summary="running",
        ),
    ]


def test_check_veritas_vcs_system() -> None:
    assert list(veritas_vcs.check_veritas_vcs_system("stuart", PARAMS, SECTION)) == [
        Result(
            state=state.OK,
            summary="running",
        ),
        Result(
            state=state.OK,
            summary="cluster: minions",
        ),
    ]


def test_check_veritas_vcs_group() -> None:
    assert list(veritas_vcs.check_veritas_vcs_group("nepharius", PARAMS, SECTION_HASHES,)) == [
        Result(
            state=state.WARN,
            summary="temporarily frozen",
        ),
        Result(
            state=state.OK,
            summary="online",
        ),
        Result(
            state=state.OK,
            summary="cluster: c7dbacpt",
        ),
    ]


def test_check_veritas_vcs_resource() -> None:
    assert list(veritas_vcs.check_veritas_vcs_resource("bob3-dg", PARAMS, SECTION,)) == [
        Result(
            state=state.WARN,
            summary="offline",
        ),
        Result(
            state=state.OK,
            summary="cluster: minions",
        ),
    ]


def test_cluster_check_veritas_vcs() -> None:
    assert list(
        veritas_vcs.cluster_check_veritas_vcs(
            "minions",
            PARAMS,
            {
                "node1": SECTION,
                "node2": SECTION_HASHES,
            },
        )
    ) == [
        Result(
            state=state.OK,
            summary="All nodes OK",
        ),
        Result(
            state=state.OK,
            notice="[node1]: running",
        ),
    ]


def test_cluster_check_veritas_vcs_system() -> None:
    assert list(
        veritas_vcs.cluster_check_veritas_vcs_system(
            "dave",
            PARAMS,
            {
                "node1": SECTION,
                "node2": SECTION_HASHES,
            },
        )
    ) == [
        Result(
            state=state.OK,
            summary="All nodes OK",
        ),
        Result(
            state=state.OK,
            notice="[node1]: running, [node2]: running",
        ),
        Result(
            state=state.OK,
            summary="cluster: c7dbacpt",
        ),
    ]


def test_cluster_check_veritas_vcs_group() -> None:
    SECTION["group"]["omd"] = [Vcs(attr="State", value="ONLINE", cluster="minions")]
    assert list(
        veritas_vcs.cluster_check_veritas_vcs_group(
            "omd",
            PARAMS,
            {
                "node1": SECTION,
                "node2": SECTION_HASHES,
            },
        )
    ) == [
        Result(
            state=state.CRIT,
            notice="[node1]: online, [node2]: frozen, online",
        ),
        Result(
            state=state.OK,
            summary="cluster: c7dbacpt",
        ),
    ]
    del SECTION["group"]["omd"]


def test_cluster_check_veritas_vcs_resource() -> None:
    SECTION["resource"]["lan_phantom"] = [Vcs(attr="State", value="OFFLINE", cluster="minions")]
    third_section: veritas_vcs.Section = {
        "resource": {"lan_phantom": [Vcs(attr="State", value="OFFLINE", cluster="minions")]}
    }
    assert list(
        veritas_vcs.cluster_check_veritas_vcs_resource(
            "lan_phantom",
            PARAMS,
            {
                "node1": SECTION,
                "node2": SECTION_HASHES,
                "node3": third_section,
            },
        )
    ) == [
        Result(state=state.OK, summary="All nodes OK"),
        Result(
            state=state.OK,
            notice="[node1]: offline, [node2]: online, [node3]: offline",
        ),
        Result(
            state=state.OK,
            summary="cluster: minions",
        ),
    ]
    del SECTION["resource"]["lan_phantom"]


@pytest.mark.parametrize(
    "section, expected_check_result",
    [
        pytest.param(
            {},
            [],
            id="No nodes/sections return no result",
        ),
        pytest.param(
            {
                "node1": {
                    "stripes": [Vcs(attr="ClusState", value="RUNNING", cluster=None)],
                },
                "node2": {
                    "stripes": [Vcs(attr="ClusState", value="RUNNING", cluster=None)],
                },
            },
            [],
            id="Item not in section returns no result",
        ),
        pytest.param(
            {
                "node1": {
                    "minions": [Vcs(attr="ClusState", value="RUNNING", cluster=None)],
                },
                "node2": {
                    "minions": [Vcs(attr="ClusState", value="RUNNING", cluster=None)],
                },
            },
            [
                Result(state=state.OK, summary="All nodes OK"),
                Result(state=state.OK, notice="[node1]: running, [node2]: running"),
            ],
            id="State is OK when all nodes have state RUNNING",
        ),
        pytest.param(
            {
                "node1": {
                    "minions": [Vcs(attr="ClusState", value="RUNNING", cluster=None)],
                },
                "node2": {
                    "minions": [Vcs(attr="ClusState", value="OFFLINE", cluster=None)],
                },
            },
            [
                Result(state=state.OK, summary="All nodes OK"),
                Result(state=state.OK, notice="[node1]: running, [node2]: offline"),
            ],
            id="State is WARN when at least one node has state RUNNING, and others are OFFLINE",
        ),
        pytest.param(
            {
                "node1": {
                    "minions": [Vcs(attr="ClusState", value="OFFLINE", cluster=None)],
                },
                "node2": {
                    "minions": [Vcs(attr="ClusState", value="OFFLINE", cluster=None)],
                },
            },
            [
                Result(state=state.WARN, summary="[node1]: offline, [node2]: offline"),
            ],
            id="State is WARN when all nodes are OFFLINE",
        ),
        pytest.param(
            {
                "node1": {
                    "minions": [Vcs(attr="ClusState", value="FAULTED", cluster=None)],
                },
                "node2": {
                    "minions": [Vcs(attr="ClusState", value="RUNNING", cluster=None)],
                },
            },
            [
                Result(state=state.CRIT, summary="[node1]: faulted, [node2]: running"),
            ],
            id="State is CRIT when at least one node has state FAULTED, and others are RUNNING",
        ),
        pytest.param(
            {
                "node1": {
                    "minions": [Vcs(attr="ClusState", value="FAULTED", cluster=None)],
                },
                "node2": {
                    "minions": [Vcs(attr="ClusState", value="OFFLINE", cluster=None)],
                },
            },
            [
                Result(state=state.CRIT, summary="[node1]: faulted, [node2]: offline"),
            ],
            id="State is CRIT when at least one node has state FAULTED, and others are OFFLINE",
        ),
    ],
)
def test_cluster_check_veritas_vcs_states(section, expected_check_result) -> None:
    assert (
        list(
            veritas_vcs.cluster_check_veritas_vcs_subsection(
                "minions",
                PARAMS,
                section,
            )
        )
        == expected_check_result
    )
