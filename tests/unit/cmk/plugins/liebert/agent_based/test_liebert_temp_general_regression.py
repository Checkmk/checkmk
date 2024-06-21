#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.liebert.agent_based.lib import Section
from cmk.plugins.liebert.agent_based.liebert_temp_general import (
    check_liebert_temp_general_testable,
    check_plugin_liebert_temp_general,
    snmp_section_liebert_temp_general,
)


def _section() -> Section[float]:
    assert (
        section := snmp_section_liebert_temp_general.parse_function(
            [
                [
                    [
                        "Actual Supply Fluid Temp Set Point",
                        "60.8",
                        "deg F",
                        "Ambient Air Temperature",
                        "21.1",
                        "deg C",
                    ],
                    [
                        "Free Cooling Utilization",
                        "0.0",
                        "%",
                        "Return Fluid Temperature",
                        "62.1",
                        "deg F",
                    ],
                    [
                        "Supply Fluid Temperature",
                        "57.2",
                        "deg F",
                        "Invalid Data for Testsing",
                        "bogus value",
                        "Unicycles",
                    ],
                ]
            ]
        )
    ) is not None
    return section


def test_discovery() -> None:
    assert list(check_plugin_liebert_temp_general.discovery_function(_section())) == [
        Service(item="Actual Supply Fluid Temp Set Point"),
        Service(item="Ambient Air Temperature"),
        Service(item="Free Cooling Utilization"),
        Service(item="Return Fluid Temperature"),
        Service(item="Supply Fluid Temperature"),
    ]


def test_check() -> None:
    assert list(
        check_liebert_temp_general_testable(
            "Actual Supply Fluid Temp Set Point", {}, _section(), {}
        )
    ) == [
        Metric("temp", 16.0),
        Result(state=State.OK, summary="Temperature: 16.0 °C"),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (no levels found)",
        ),
    ]
