#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State


@pytest.fixture(name="section_1", scope="module")
def _get_section_1(fix_register):
    return fix_register.agent_sections[SectionName("heartbeat_crm")].parse_function(
        [
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
    )


@pytest.fixture(name="section_2", scope="module")
def _get_section_2(fix_register):
    return fix_register.agent_sections[SectionName("heartbeat_crm")].parse_function(
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


@pytest.fixture(name="discover_heartbeat_crm_resources")
def _get_discovery_function_resources(fix_register):
    return fix_register.check_plugins[CheckPluginName("heartbeat_crm_resources")].discovery_function


@pytest.fixture(name="check_heartbeat_crm_resources")
def _get_check_function_resources(fix_register):
    return lambda i, p, s: fix_register.check_plugins[
        CheckPluginName("heartbeat_crm_resources")
    ].check_function(item=i, params=p, section=s)


# enable/fix once migrated
#
# def test_discovery_heartbeat_crm_resources_nothing(section_1, discover_heartbeat_crm_resources) -> None:
#    assert not list(discover_heartbeat_crm_resources(section_1))
#
# def test_discovery_heartbeat_crm_resources_something(section_2, discover_heartbeat_crm_resources) -> None:
#    assert list(discover_heartbeat_crm_resources(section_2)) == []
#


def test_check_heartbeat_crm_resources_no_data(section_2, check_heartbeat_crm_resources) -> None:
    assert not list(check_heartbeat_crm_resources("no such item", {}, section_2))


def test_check_heartbeat_crm_resources_no_resources(
    section_2, check_heartbeat_crm_resources
) -> None:
    section_2.resources.resources["faked empty ressource"] = []
    assert list(check_heartbeat_crm_resources("faked empty ressource", {}, section_2)) == [
        Result(state=State.OK, summary="No resources found")
    ]


def test_check_heartbeat_crm_resources_ok(section_1, check_heartbeat_crm_resources) -> None:
    assert list(check_heartbeat_crm_resources("clone_nfs_sapmnt_IFG", {}, section_1)) == [
        Result(state=State.OK, summary="clone_nfs_sapmnt_IFG Clone Started hrssc61i01, hrssc61i02"),
    ]


def test_check_heartbeat_crm_resources_started(section_2, check_heartbeat_crm_resources) -> None:
    assert list(
        check_heartbeat_crm_resources(
            "cluster1_fence(stonith:fence_ipmilan):",
            {},
            section_2,
        )
    ) == [
        Result(state=State.OK, summary="cluster1_fence(stonith:fence_ipmilan): Started cluster2"),
        # TODO: check if this maaaaaybe should read 'state "Started"'
        Result(state=State.CRIT, summary='Resource is in state "cluster2"'),
    ]
