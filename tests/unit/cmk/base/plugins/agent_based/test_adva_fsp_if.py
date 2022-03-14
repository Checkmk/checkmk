#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import adva_fsp_if
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State

SECTION = {
    "CH-1-4-C1": {
        "type": "1",
        "admin_status": "1",
        "oper_status": "1",
        "output": "-31",
        "input": "-27",
    },
    "CH-1-4-NE": {
        "type": "1",
        "admin_status": "1",
        "oper_status": "1",
        "output": "22",
        "input": "-120",
    },
    "SC-1-A-C1": {
        "type": "6",
        "admin_status": "2",
        "oper_status": "2",
        "output": "-65535",
        "input": "-65535",
    },
    "LINK-1-A-SER": {
        "type": "141",
        "admin_status": "1",
        "oper_status": "1",
        "output": "",
        "input": "",
    },
    "SH-1-3-I1": {
        "type": "1",
        "admin_status": "1",
        "oper_status": "1",
        "output": "",
        "input": "",
    },
    "CH-1-4-I2": {
        "type": "1",
        "admin_status": "1",
        "oper_status": "5",
        "output": "",
        "input": "",
    },
}


def test_discover_adva_fsp_if():
    assert list(adva_fsp_if.discover_adva_fsp_if(SECTION)) == [
        Service(item="CH-1-4-C1", parameters={}, labels=[]),
        Service(item="CH-1-4-NE", parameters={}, labels=[]),
        Service(item="SH-1-3-I1", parameters={}, labels=[]),
        Service(item="CH-1-4-I2", parameters={}, labels=[]),
    ]


@pytest.mark.parametrize(
    "item, params, expected_result",
    [
        (
            "CH-1-4-C1",
            {},
            [
                Result(
                    state=State.OK,
                    summary="Admin/Operational State: up/up",
                    details="Admin/Operational State: up/up",
                ),
                Result(state=State.OK, summary="Output power: -3.1 dBm"),
                Metric("output_power", -3.1, boundaries=(0.0, None)),
                Result(
                    state=State.OK, summary="Input power: -2.7 dBm", details="Input power: -2.7 dBm"
                ),
                Metric("input_power", -2.7, boundaries=(0.0, None)),
            ],
        ),
        (
            "CH-1-4-NE",
            {
                "limits_output_power": (0.0, 1.0),
                "limits_input_power": (-5.2, 12.3),
            },
            [
                Result(
                    state=State.OK,
                    summary="Admin/Operational State: up/up",
                    details="Admin/Operational State: up/up",
                ),
                Result(state=State.CRIT, summary="Output power: 2.2 dBm"),
                Metric("output_power", 2.2, levels=(None, 1.0), boundaries=(0.0, None)),
                Result(
                    state=State.CRIT,
                    summary="Input power: -12.0 dBm",
                    details="Input power: -12.0 dBm",
                ),
                Metric("input_power", -12.0, levels=(None, 12.3), boundaries=(0.0, None)),
            ],
        ),
        (
            "SH-1-3-I1",
            {},
            [
                Result(
                    state=State.OK,
                    summary="Admin/Operational State: up/up",
                    details="Admin/Operational State: up/up",
                ),
            ],
        ),
        (
            "CH-1-4-I2",
            {},
            [
                Result(
                    state=State.WARN,
                    summary="Admin/Operational State: up/dormant",
                    details="Admin/Operational State: up/dormant",
                ),
                Result(state=State.WARN, summary="Output power: n.a."),
                Result(state=State.WARN, summary="Input power: n.a."),
            ],
        ),
    ],
)
def test_check_huawei_osn_if(item, params, expected_result):
    assert (
        list(
            adva_fsp_if.check_adva_fsp_if(
                item,
                params,
                SECTION,
            )
        )
        == expected_result
    )
