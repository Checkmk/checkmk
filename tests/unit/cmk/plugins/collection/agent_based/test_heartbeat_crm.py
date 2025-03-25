#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.collection.agent_based.heartbeat_crm import (
    _check_heartbeat_crm,
    _check_heartbeat_crm_resources,
    check_heartbeat_crm_resources,
    discover_heartbeat_crm,
    heartbeat_crm_parse_resources,
    HeartbeatCrmResourcesParameters,
    parse_heartbeat_crm,
    Section,
)


@pytest.fixture(name="section_1", scope="module")
def _get_section_1() -> Section:
    section = parse_heartbeat_crm(
        [
            ["Cluster", "Summary:"],
            ["_*", "Stack:", "corosync"],
            [
                "_*",
                "Current",
                "DC:",
                "ha02",
                "(version",
                "2.0.3-5.el8_2.1-4b1f869f0f)",
                "-",
                "partition",
                "with",
                "quorum",
            ],
            ["_*", "Last", "updated:", "Tue", "Sep", "8", "10:36:12", "2020"],
            [
                "_*",
                "Last",
                "change:",
                "Mon",
                "Sep",
                "7",
                "22:33:23",
                "2020",
                "by",
                "root",
                "via",
                "cibadmin",
                "on",
                "ha01",
            ],
            ["_*", "2", "nodes", "configured"],
            ["_*", "3", "resource", "instances", "configured"],
            ["Node", "List:"],
            ["_*", "Online:", "[", "ha01", "ha02", "]"],
            ["Full", "List", "of", "Resources:"],
            ["_*", "vip", "(ocf::heartbeat:IPaddr):", "Started", "ha01"],
            ["_*", "Clone", "Set:", "splunk-clone", "[splunk]:"],
            ["_", "*", "Started:", "[", "ha01", "ha02", "]"],
        ]
    )
    assert section
    return section


@pytest.fixture(name="section_2", scope="module")
def _get_section_2() -> Section:
    section = parse_heartbeat_crm(
        [
            ["Stack:", "corosync"],
            [
                "Current",
                "DC:",
                "cluster",
                "(version",
                "1.1.16-12.el7_4.8-94ff4df)",
                "-",
                "partition",
                "with",
                "quorum",
            ],
            ["Last", "updated:", "Tue", "Oct", "26", "13:58:47", "2019"],
            [
                "Last",
                "change:",
                "Sat",
                "Oct",
                "24",
                "10:54:28",
                "2019",
                "by",
                "root",
                "via",
                "cibadmin",
                "on",
                "cluster",
            ],
            ["2", "nodes", "configured"],
            ["6", "resources", "configured"],
            ["Online:", "[", "cluster1", "cluster2", "]"],
            ["Full", "list", "of", "resources:"],
            ["Resource", "Group:", "mysqldb1"],
            ["_", "mysqldb1_lvm", "(ocf::heartbeat:LVM):Started", "cluster1"],
            ["_", "mysqldb1_fs", "(ocf::heartbeat:Filesystem):Started", "cluster1"],
            ["_", "mysqldb1_ip", "(ocf::heartbeat:IPaddr2):Started", "cluster1"],
            ["_", "mysqldb1_mysql", "(service:mysqldb1):Started", "cluster1"],
            ["cluster1_fence(stonith:fence_ipmilan):", "Started", "cluster2"],
            ["cluster2_fence(stonith:fence_ipmilan):", "Started", "cluster1"],
            ["Failed", "Actions:"],
            [
                "*",
                "mysqldb1_lvm_monitor_10000",
                "on",
                "cluster1",
                "'unknown",
                "error'",
                "(1):",
                "call=158,",
                "status=Timed",
                "Out,",
                "exitreason='none',",
            ],
            [
                "_",
                "last-rc-change='Fri",
                "Feb",
                "22",
                "22:54:52",
                "2019',",
                "queued=0ms,",
                "exec=0ms",
            ],
        ]
    )
    assert section
    return section


@pytest.fixture(name="section_3", scope="module")
def _get_section_3() -> Section:
    section = parse_heartbeat_crm(
        [
            ["Stack:", "corosync"],
            [
                "Current",
                "DC:",
                "ha_b",
                "(version",
                "2.0.1-9e909a5bdd)",
                "-",
                "partition",
                "WITHOUT",
                "quorum",
            ],
            ["Last", "updated:", "Thu", "Aug", "11", "08:39:19", "2022"],
            [
                "Last",
                "change:",
                "Thu",
                "Aug",
                "11",
                "09:29:04",
                "2022",
                "by",
                "root",
                "via",
                "crm_resource",
                "on",
                "ha_b",
            ],
            ["2", "nodes", "configured"],
            ["7", "resources", "configured"],
            ["Online:", "[", "ha_b", "]"],
            ["OFFLINE:", "[", "ha_a", "]"],
            ["Full", "list", "of", "resources:"],
            ["Clone", "Set:", "clone_1", "[pri_clone_1]", "(promotable)"],
            ["_", "Masters:", "[", "ha_b", "]"],
            ["_", "Stopped:", "[", "ha_a", "]"],
            ["Clone", "Set:", "clone_ping", "[pri_ping]"],
            ["_", "Started:", "[", "ha_b", "]"],
            ["_", "Stopped:", "[", "ha_a", "]"],
            ["Resource", "Group:", "grp_omd"],
            ["_", "pri_fs_omd", "(ocf::heartbeat:Filesystem):", "Started", "ha_b"],
            ["_", "pri_ip_omd", "(ocf::heartbeat:IPaddr2):", "Started", "ha_b"],
            ["_", "pri_proc_omd", "(ocf::mk:omd):", "Stopped"],
            ["Failed", "Resource", "Actions:"],
            [
                "*",
                "pri_proc_omd_start_0",
                "on",
                "ha_b",
                "'unknown",
                "error'",
                "(1):",
                "call=35,",
                "status=complete,",
                "exitreason='',",
            ],
            [
                "_",
                "last-rc-change='Thu",
                "Aug",
                "11",
                "07:52:05",
                "2022',",
                "queued=0ms,",
                "exec=846ms",
            ],
        ]
    )
    assert section
    return section


def test_discover_heartbeat_crm(section_1: Section) -> None:
    assert list(discover_heartbeat_crm({"naildown_dc": False}, section_1)) == [
        Service(parameters={"num_nodes": 2, "num_resources": 3}),
    ]


def test_discovery_heartbeat_crm_dc_naildown(section_1: Section) -> None:
    assert list(discover_heartbeat_crm({"naildown_dc": True}, section_1)) == [
        Service(parameters={"num_nodes": 2, "num_resources": 3, "dc": "ha02"}),
    ]


def test_check_heartbeat_crm_too_old(section_1: Section) -> None:
    assert list(
        _check_heartbeat_crm(
            {"max_age": 60, "num_nodes": 2, "num_resources": 3},
            section_1,
            1601339704.5458105,
        )
    ) == [
        Result(
            state=State.CRIT,
            summary="Ignoring reported data (Status output too old: 20 days 13 hours)",
        )
    ]


def test_check_heartbeat_crm_ok(section_1: Section) -> None:
    with time_machine.travel(datetime.datetime(2020, 9, 8, 10, 36, 36, tzinfo=ZoneInfo("UTC"))):
        assert list(
            _check_heartbeat_crm(
                {"max_age": 60, "num_nodes": 2, "num_resources": 3},
                section_1,
                1589939704.5458105,
            )
        ) == [
            Result(state=State.OK, summary="DC: ha02"),
            Result(state=State.OK, summary="Nodes: 2"),
            Result(state=State.OK, summary="Resources: 3"),
        ]


def test_check_heartbeat_crm_crit(section_2: Section) -> None:
    with time_machine.travel(datetime.datetime(2019, 8, 18, 10, 36, 36, tzinfo=ZoneInfo("UTC"))):
        assert list(
            _check_heartbeat_crm(
                {
                    "dc": "hasi",
                    "max_age": 60,
                    "num_nodes": 1,
                    "num_resources": 4,
                    "show_failed_actions": True,
                },
                section_2,
                1559939704.5458105,
            )
        ) == [
            Result(state=State.CRIT, summary="DC: cluster (Expected hasi)"),
            Result(state=State.CRIT, summary="Nodes: 2 (Expected 1)"),
            Result(state=State.CRIT, summary="Resources: 6 (Expected 4)"),
            Result(
                state=State.WARN,
                summary=(
                    "Failed: mysqldb1_lvm_monitor_10000 on cluster1 'unknown error' (1): call=158, "
                    "status=Timed Out, exitreason='none', "
                    "last-rc-change='Fri Feb 22 22:54:52 2019', queued=0ms, exec=0ms"
                ),
            ),
        ]


def test_check_heartbeat_crm_resources_promotable_clone(section_3: Section) -> None:
    assert list(
        check_heartbeat_crm_resources(
            "clone_1",
            HeartbeatCrmResourcesParameters(
                expected_node=None,
                monitoring_state_if_unmanaged_nodes=1,
            ),
            section_3,
        )
    ) == [Result(state=State.OK, summary="clone_1 Master Started ha_b")]


def test_check_heartbeat_crm_resources_simple(section_3: Section) -> None:
    assert list(
        check_heartbeat_crm_resources(
            "grp_omd",
            HeartbeatCrmResourcesParameters(
                expected_node=None,
                monitoring_state_if_unmanaged_nodes=1,
            ),
            section_3,
        )
    ) == [
        Result(state=State.OK, summary="pri_fs_omd (ocf::heartbeat:Filesystem): Started ha_b"),
        Result(state=State.OK, summary="pri_ip_omd (ocf::heartbeat:IPaddr2): Started ha_b"),
        Result(state=State.OK, summary="pri_proc_omd (ocf::mk:omd): Stopped"),
        Result(state=State.CRIT, summary='Resource is in state "Stopped"'),
    ]


def test_check_heartbeat_crm_resources_only() -> None:
    resources = heartbeat_crm_parse_resources(
        # data from SUP-14949
        [
            ["Resource", "Group:", "checkmk"],
            [
                "_",
                "checkmk_lvm",
                "(ocf::heartbeat:LVM):",
                "Started",
                "xxxxxxxx-rrrrr",
                "(unmanaged)",
            ],
            [
                "_",
                "checkmk_fs",
                "(ocf::heartbeat:Filesystem):",
                "Started",
                "xxxxxxxx-rrrrr",
                "(unmanaged)",
            ],
            [
                "_",
                "checkmk_ip_1002",
                "(ocf::heartbeat:IPaddr2):",
                "Started",
                "xxxxxxxx-rrrrr",
                "(unmanaged)",
            ],
            [
                "_",
                "checkmk_ip_1000",
                "(ocf::heartbeat:IPaddr2):",
                "Started",
                "xxxxxxxx-rrrrr",
                "(unmanaged)",
            ],
            [
                "_",
                "checkmk_http",
                "(systemd:httpd):",
                "Started",
                "xxxxxxxx-rrrrr",
                "(unmanaged)",
            ],
            [
                "_",
                "checkmk_omd",
                "(ocf::custom:omd):",
                "Stopped",
                "(unmanaged)",
            ],
        ]
    )
    assert list(
        _check_heartbeat_crm_resources(
            resources["checkmk"],
            HeartbeatCrmResourcesParameters(
                expected_node=None,
                monitoring_state_if_unmanaged_nodes=1,
            ),
        )
    ) == [
        Result(
            state=State.OK,
            summary="checkmk_lvm (ocf::heartbeat:LVM): Started xxxxxxxx-rrrrr (unmanaged)",
        ),
        Result(
            state=State.OK,
            summary="checkmk_fs (ocf::heartbeat:Filesystem): Started xxxxxxxx-rrrrr (unmanaged)",
        ),
        Result(
            state=State.OK,
            summary="checkmk_ip_1002 (ocf::heartbeat:IPaddr2): Started xxxxxxxx-rrrrr (unmanaged)",
        ),
        Result(
            state=State.OK,
            summary="checkmk_ip_1000 (ocf::heartbeat:IPaddr2): Started xxxxxxxx-rrrrr (unmanaged)",
        ),
        Result(
            state=State.OK,
            summary="checkmk_http (systemd:httpd): Started xxxxxxxx-rrrrr (unmanaged)",
        ),
        Result(state=State.OK, summary="checkmk_omd (ocf::custom:omd): Stopped (unmanaged)"),
        Result(state=State.CRIT, summary='Resource is in state "Stopped"'),
        Result(
            state=State.WARN,
            summary="Unmanaged nodes: xxxxxxxx-rrrrr",
        ),
    ]
