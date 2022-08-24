#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

from tests.unit.checks.checktestlib import MockHostExtraConf
from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable


@pytest.fixture(name="heartbeat_crm_resources_check")
def _heartbeat_crm_resources_check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("heartbeat_crm_resources")]


@pytest.fixture(name="section_1")
def _get_section_1() -> StringTable:
    return [
        ["Stack:", "corosync"],
        [
            "Current",
            "DC:",
            "hrssc61i02",
            "(version",
            "1.1.19+20180928.0d2680780-1.8-1.1.19+20180928.0d2680780)",
            "-",
            "partition",
            "with",
            "quorum",
        ],
        ["Last", "updated:", "Mon", "Mar", "11", "14:17:33", "2019"],
        [
            "Last",
            "change:",
            "Thu",
            "Feb",
            "28",
            "17:40:07",
            "2019",
            "by",
            "hacluster",
            "via",
            "cibadmin",
            "on",
            "hrssc61i01",
        ],
        ["2", "nodes", "configured"],
        ["10", "resources", "configured"],
        ["Online:", "[", "hrssc61i01", "hrssc61i02", "]"],
        ["Full", "list", "of", "resources:"],
        ["Resource", "Group:", "grp_IFG_ASCS22"],
        ["_", "rsc_ip_IFG_ASCS22", "(ocf::heartbeat:IPaddr2):", "Started", "hrssc61i01"],
        ["_", "rsc_sap_IFG_ASCS22", "(ocf::heartbeat:SAPInstance):", "Started", "hrssc61i01"],
        ["Resource", "Group:", "grp_IFG_ERS23"],
        ["_", "rsc_ip_IFG_ERS23", "(ocf::heartbeat:IPaddr2):", "Started", "hrssc61i02"],
        ["_", "rsc_sap_IFG_ERS23", "(ocf::heartbeat:SAPInstance):", "Started", "hrssc61i02"],
        ["Clone", "Set:", "clone_nfs_sapmnt_IFG", "[nfs_sapmnt_IFG]"],
        ["_", "Started:", "[", "hrssc61i01", "hrssc61i02", "]"],
        ["Clone", "Set:", "clone_nfs_usr_sap_IFG", "[nfs_usr_sap_IFG]"],
        ["_", "Started:", "[", "hrssc61i01", "hrssc61i02", "]"],
        ["st-vmware", "(stonith:fence_vmware_rest):", "Started", "hrssc61i02"],
        ["st-vmware2", "(stonith:fence_vmware_rest):", "Started", "hrssc61i01"],
        ["Failed", "Resource", "Actions:"],
        [
            "*",
            "st-vmware_monitor_20000",
            "on",
            "hrssc61i02",
            "'unknown",
            "error'",
            "(1):",
            "call=43,",
            "status=Error,",
            "exitreason='',",
        ],
        [
            "_",
            "last-rc-change='Mon",
            "Mar",
            "4",
            "09:29:54",
            "2019',",
            "queued=0ms,",
            "exec=11096ms",
        ],
        [
            "*",
            "st-vmware2_monitor_20000",
            "on",
            "hrssc61i01",
            "'unknown",
            "error'",
            "(1):",
            "call=43,",
            "status=Error,",
            "exitreason='',",
        ],
        [
            "_",
            "last-rc-change='Mon",
            "Mar",
            "4",
            "09:29:54",
            "2019',",
            "queued=0ms,",
            "exec=11088ms",
        ],
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


@pytest.fixture(name="section_pacemaker_v2")
def _section_pacemaker_v2() -> StringTable:
    return [
        ["Cluster", "Summary:"],
        ["_*", "Stack:", "corosync"],
        [
            "_*",
            "Current",
            "DC:",
            "cbgdevd01",
            "(version",
            "2.1.2-4.el8_6.2-ada5c3b36e2)",
            "-",
            "partition",
            "with",
            "quorum",
        ],
        ["_*", "Last", "updated:", "Tue", "Aug", "23", "05:14:00", "2022"],
        [
            "_*",
            "Last",
            "change:",
            "Mon",
            "Aug",
            "22",
            "10:11:00",
            "2022",
            "by",
            "hacluster",
            "via",
            "crmd",
            "on",
            "cbgdevd01",
        ],
        ["_*", "2", "nodes", "configured"],
        ["_*", "6", "resource", "instances", "configured"],
        ["Node", "List:"],
        ["_*", "Online:", "[", "cbgdevd01", "cbgdevd02", "]"],
        ["Full", "List", "of", "Resources:"],
        ["_*", "rhevfence", "(stonith:fence_rhevm):", "Started", "cbgdevd01"],
        ["_*", "Resource", "Group:", "QPID:"],
        ["_", "*", "qpid_lvm", "(ocf::heartbeat:LVM-activate):", "Started", "cbgdevd01"],
        ["_", "*", "qpid_fs", "(ocf::heartbeat:Filesystem):", "Started", "cbgdevd01"],
        ["_", "*", "qpid_ip", "(ocf::heartbeat:IPaddr2):", "Started", "cbgdevd01"],
        ["_", "*", "qpid_jb", "(ocf::custom:AmqpService):", "Started", "cbgdevd01"],
        ["_*", "Resource", "Group:", "BRIDGE:"],
        [
            "_",
            "*",
            "bridge_bb",
            "(ocf::custom:AmqpService):",
            "Started",
            "cbgdevd02",
            "(unmanaged)",
        ],
    ]


def test_discovery_heartbeat_crm_resources_nothing() -> None:
    heartbeat_crm_resources_check = Check("heartbeat_crm.resources")

    with MockHostExtraConf(
        heartbeat_crm_resources_check,
        lambda _h, _r: {},
        "host_extra_conf_merged",
    ):
        discovery_result = list(heartbeat_crm_resources_check.run_discovery([]))

    assert not discovery_result


def test_discovery_heartbeat_crm_resources_something(section_2: StringTable) -> None:
    heartbeat_crm_resources_check = Check("heartbeat_crm.resources")

    with MockHostExtraConf(
        heartbeat_crm_resources_check,
        lambda _h, _r: {},
        "host_extra_conf_merged",
    ):
        discovery_result = list(heartbeat_crm_resources_check.run_discovery(section_2))

    assert discovery_result == [
        ("mysqldb1", None),
        ("cluster1_fence(stonith:fence_ipmilan):", None),
        ("cluster2_fence(stonith:fence_ipmilan):", None),
    ]


def test_check_heartbeat_crm_resources_no_data(
    section_2: StringTable, heartbeat_crm_resources_check: CheckPlugin
) -> None:
    assert not list(
        heartbeat_crm_resources_check.check_function(
            item="no such item", params={}, section=section_2
        )
    )


def test_check_heartbeat_crm_resources_ok(
    section_1: StringTable, heartbeat_crm_resources_check: CheckPlugin
) -> None:
    assert list(
        heartbeat_crm_resources_check.check_function(
            item="clone_nfs_sapmnt_IFG",
            params={
                "expected_node": "nevermind",
            },
            section=section_1,
        )
    ) == [
        Result(state=State.OK, summary="clone_nfs_sapmnt_IFG Clone Started hrssc61i01, hrssc61i02"),
    ]


def test_check_heartbeat_crm_resources_started(
    section_2: StringTable, heartbeat_crm_resources_check: CheckPlugin
) -> None:
    assert list(
        heartbeat_crm_resources_check.check_function(
            item="cluster1_fence(stonith:fence_ipmilan):",
            params={},
            section=section_2,
        )
    ) == [
        Result(state=State.OK, summary="cluster1_fence(stonith:fence_ipmilan): Started cluster2"),
        # TODO: check if this maaaaaybe should read 'state "Started"'
        Result(state=State.CRIT, summary='Resource is in state "cluster2"'),
    ]


def test_discover_heartbeat_crm_resources_pacemaker_v2(section_pacemaker_v2: StringTable) -> None:
    heartbeat_crm_resources_check = Check("heartbeat_crm.resources")
    expected_services = [("rhevfence", None), ("QPID", None), ("BRIDGE", None)]

    with MockHostExtraConf(
        heartbeat_crm_resources_check,
        lambda _h, _r: {},
        "host_extra_conf_merged",
    ):
        discovered_services = list(
            heartbeat_crm_resources_check.run_discovery(section_pacemaker_v2)
        )

    assert discovered_services == expected_services
