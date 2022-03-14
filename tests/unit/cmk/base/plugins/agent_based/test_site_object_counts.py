#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based import site_object_counts
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state

SECTION: site_object_counts.Section = {
    "heute": {"Service check commands": {"lnx_if": 3, "omd_apache": 2}, "Tags": {"snmp": 1}},
    "stable": {
        "Service check commands": {"hr_cpu": 1, "omd_apache": 2},
        "Tags": {"prod": 2, "snmp": 2},
    },
}


def test_parse_site_object_counts():
    assert (
        site_object_counts.parse_site_object_counts(
            [
                ["[[[heute]]]"],
                ["Tags", "snmp", "1"],
                ["Service check commands", "omd_apache lnx_if", "2;3"],
                ["[[[stable]]]"],
                ["Tags", "snmp prod", "2;2"],
                ["Service check commands", "omd_apache hr_cpu", "2;1"],
                ["[[[old]]]"],
            ]
        )
        == SECTION
    )


def test_check_site_object_counts():
    assert list(site_object_counts.check_site_object_counts(SECTION)) == [
        Result(
            state=state.OK,
            notice="[heute] Service Check Commands: 3 lnx_if, 2 omd_apache, Tags: 1 snmp",
        ),
        Result(
            state=state.OK,
            notice="[stable] Service Check Commands: 1 hr_cpu, 2 omd_apache, Tags: 2 prod, 2 snmp",
        ),
        Metric("service_check_commands_lnx_if", 3.0),
        Metric(
            "service_check_commands_omd_apache", 4.0, levels=(None, None), boundaries=(None, None)
        ),
        Metric("service_check_commands_hr_cpu", 1.0),
        Metric("tags_snmp", 3.0),
        Metric("tags_prod", 2.0),
        Result(
            state=state.OK,
            summary="Service Check Commands: 3 lnx_if, 4 omd_apache, 1 hr_cpu, Tags: 3 snmp, 2 prod",
            details="Service Check Commands: 3 lnx_if, 4 omd_apache, 1 hr_cpu, Tags: 3 snmp, 2 prod",
        ),
    ]


def test_cluster_check_site_object_counts():
    assert list(
        site_object_counts.cluster_check_site_object_counts(
            {
                "node1": SECTION,
                "node2:": {
                    "stable": {
                        "Service check commands": {"hr_cpu": 3, "lnx_if": 2},
                        "Tags": {
                            "prod": 2,
                            "tcp": 5,
                        },
                    },
                },
            }
        )
    ) == [
        Result(
            state=state.OK,
            notice="[heute/node1] Service Check Commands: 3 lnx_if, 2 omd_apache, Tags: 1 snmp",
        ),
        Result(
            state=state.OK,
            notice="[stable/node1] Service Check Commands: 1 hr_cpu, 2 omd_apache, Tags: 2 prod, 2 snmp",
        ),
        Result(
            state=state.OK,
            notice="[stable/node2:] Service Check Commands: 3 hr_cpu, 2 lnx_if, Tags: 2 prod, 5 tcp",
        ),
        Metric("service_check_commands_lnx_if", 5.0),
        Metric(
            "service_check_commands_omd_apache", 4.0, levels=(None, None), boundaries=(None, None)
        ),
        Metric("service_check_commands_hr_cpu", 4.0),
        Metric("tags_snmp", 3.0),
        Metric("tags_prod", 4.0),
        Metric("tags_tcp", 5.0),
        Result(
            state=state.OK,
            summary="Service Check Commands: 5 lnx_if, 4 omd_apache, 4 hr_cpu, Tags: 3 snmp, 4 prod, 5 tcp",
            details="Service Check Commands: 5 lnx_if, 4 omd_apache, 4 hr_cpu, Tags: 3 snmp, 4 prod, 5 tcp",
        ),
    ]
