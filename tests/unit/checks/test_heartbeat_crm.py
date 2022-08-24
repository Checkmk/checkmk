#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check, on_time

from tests.unit.checks.checktestlib import MockHostExtraConf
from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable


@pytest.fixture(name="heartbeat_crm_check")
def _heartbeat_crm_check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("heartbeat_crm")]


@pytest.fixture(name="section_1")
def _get_section_1() -> StringTable:
    return [
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


@pytest.fixture(name="section_2")
def _get_section_2() -> StringTable:
    return [
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


def test_discover_heartbeat_crm(section_1: StringTable) -> None:
    heartbeat_crm_check = Check("heartbeat_crm")

    with MockHostExtraConf(
        heartbeat_crm_check, lambda _h, _r: {"naildown_dc": False}, "host_extra_conf_merged"
    ):
        discovery_result = list(heartbeat_crm_check.run_discovery(section_1))

    assert discovery_result == [(None, {"num_nodes": 2, "num_resources": 3})]


def test_discovery_heartbeat_crm_dc_naildown(section_1: StringTable) -> None:
    heartbeat_crm_check = Check("heartbeat_crm")

    with MockHostExtraConf(
        heartbeat_crm_check, lambda _h, _r: {"naildown_dc": True}, "host_extra_conf_merged"
    ):
        discovery_result = list(heartbeat_crm_check.run_discovery(section_1))

    assert discovery_result == [(None, {"num_nodes": 2, "num_resources": 3, "dc": "ha02"})]


def test_check_heartbeat_crm_too_old(
    section_1: StringTable, heartbeat_crm_check: CheckPlugin
) -> None:
    (result,) = heartbeat_crm_check.check_function(
        params={"max_age": 60, "num_nodes": 2, "num_resources": 3},
        section=section_1,
    )

    assert isinstance(result, Result)
    assert result.state is State.CRIT
    # Note: going crit is not the same as ignoring data.
    assert result.summary.startswith("Ignoring reported data ")


def test_check_heartbeat_crm_ok(section_1: StringTable, heartbeat_crm_check: CheckPlugin) -> None:
    with on_time("2020-09-08 10:36:36", "UTC"):
        assert list(
            heartbeat_crm_check.check_function(
                params={"max_age": 60, "num_nodes": 2, "num_resources": 3, "dc": None},
                section=section_1,
            )
        ) == [
            Result(state=State.OK, summary="DC: ha02"),
            Result(state=State.OK, summary="Nodes: 2"),
            Result(state=State.OK, summary="Resources: 3"),
        ]


def test_check_heartbeat_crm_crit(section_2: StringTable, heartbeat_crm_check: CheckPlugin) -> None:
    with on_time("2019-08-18 10:36:36", "UTC"):
        assert list(
            heartbeat_crm_check.check_function(
                params={
                    "dc": "hasi",
                    "max_age": 60,
                    "num_nodes": 1,
                    "num_resources": 4,
                    "show_failed_actions": True,
                },
                section=section_2,
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
