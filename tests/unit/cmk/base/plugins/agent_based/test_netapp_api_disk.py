#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State

_AGENT_OUTPUT = [
    [
        "disk 123:456",
        "physical-space 1000",
        "used-space 500",
        "raid-type data",
        "raid-state aggregate",
        "serial-number ABC:DEF",
        "vendor-id NetApp",
    ],
    # 'remote' will be sorted out
    [
        "disk remote:123:456",
        "physical-space 1000",
        "used-space 500",
        "raid-type data",
        "raid-state remote",
        "serial-number remote:ABC:DEF",
        "vendor-id NetApp",
    ],
    # 'partner' will be sorted out
    [
        "disk partner:123:456",
        "physical-space 1000",
        "used-space 500",
        "raid-type data",
        "raid-state partner",
        "serial-number oartner:ABC:DEF",
        "vendor-id NetApp",
    ],
]


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (_AGENT_OUTPUT, [Service()]),
    ],
)
def test_discover_netapp_api_disk(fix_register, string_table, expected_result):
    check_plugin = fix_register.check_plugins[CheckPluginName("netapp_api_disk_summary")]
    assert sorted(check_plugin.discovery_function(string_table)) == expected_result


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (
            _AGENT_OUTPUT,
            [
                Result(state=State.OK, summary="Total raw capacity: 1000.00 B"),
                Metric("total_disk_capacity", 1000.0),
                Result(state=State.OK, summary="Total disks: 1"),
                Metric("total_disks", 1.0),
                Result(state=State.OK, summary="Spare disks: 0"),
                Metric("spare_disks", 0.0),
                Result(state=State.OK, summary="Failed disks: 0"),
                Metric("failed_disks", 0.0),
                Result(state=State.OK, summary="1 disks"),
            ],
        ),
    ],
)
def test_check_netapp_api_disk(fix_register, string_table, expected_result):
    check_plugin = fix_register.check_plugins[CheckPluginName("netapp_api_disk_summary")]
    assert list(check_plugin.check_function(params={}, section=string_table)) == expected_result
