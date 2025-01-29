#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.lib.temperature import TempParamDict
from cmk.plugins.liebert.agent_based.liebert_temp_fluid import (
    check_liebert_temp_fluid,
    discover_liebert_temp_fluid,
    parse_liebert_temp_fluid,
    Section,
)


@pytest.fixture(name="section", scope="module")
def _section() -> Section:
    return parse_liebert_temp_fluid(
        [
            [
                "Supply Fluid Temp Set Point 1",
                "14.0",
                "deg C",
                "Supply Fluid Temp Set Point 2",
                "-6",
                "deg C",
                "Supply Fluid Over Temp Alarm Threshold",
                "0",
                "deg C",
                "Supply Fluid Under Temp Warning Threshold",
                "0",
                "deg C",
                "Supply Fluid Under Temp Alarm Threshold",
                "0",
                "deg C",
                "Supply Fluid Over Temp Warning Threshold",
                "32",
                "deg F",
            ]
        ]
    )


def test_discover(section: Section) -> None:
    assert list(discover_liebert_temp_fluid(section)) == [
        Service(item="Supply Fluid Temp Set Point 1"),
        Service(item="Supply Fluid Temp Set Point 2"),
    ]


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    ["item", "params", "expected_result"],
    [
        pytest.param(
            "Supply Fluid Temp Set Point 1",
            {},
            [
                Metric("temp", 14.0, levels=(0.0, 0.0)),
                Result(
                    state=State.CRIT, summary="Temperature: 14.0 °C (warn/crit at 0.0 °C/0.0 °C)"
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
            ],
            id="default params",
        ),
        pytest.param(
            "Supply Fluid Temp Set Point 2",
            {
                "levels": (20, 30),
                "device_levels_handling": "usr",
            },
            [
                Metric("temp", -6.0, levels=(20.0, 30.0)),
                Result(state=State.OK, summary="Temperature: -6.0 °C"),
                Result(state=State.OK, notice="Configuration: only use user levels"),
            ],
            id="custom thresholds",
        ),
    ],
)
def test_check(
    item: str,
    params: TempParamDict,
    section: Section,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_liebert_temp_fluid(
                item=item,
                params=params,
                section=section,
            )
        )
        == expected_result
    )
