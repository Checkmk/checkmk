#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import typing

import pytest
import time_machine

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.temperature import TempParamDict, TrendComputeDict
from cmk.plugins.liebert.agent_based.lib import SystemSection
from cmk.plugins.liebert.agent_based.liebert_temp_air import (
    _check_liebert_temp_air,
    discover_liebert_temp_air,
    parse_liebert_temp_air,
    ParsedSection,
)

STRING_TABLE = [
    [
        [
            "Return Air Temperature",
            "107.6",
            "deg F",
            "Some made-up Air Temperature",
            "Unavailable",
            "deg C",
        ]
    ]
]

PARAMETERS: TempParamDict = {
    "levels": (50, 55),
    "levels_lower": (10, 15),
}

PARSED_SECTION = {
    "Return Air Temperature": ("107.6", "deg F"),
    "Some made-up Air Temperature": ("Unavailable", "deg C"),
}

PARSED_EXTRA_SECTION = {
    "System Model Number": "Liebert CRV",
    "System Status": "Normal Operation",
    "Unit Operating State": "standby",
    "Unit Operating State Reason": "Reason Unknown",
}


@pytest.mark.parametrize(
    "string_table, result",
    [
        (
            STRING_TABLE,
            PARSED_SECTION,
        ),
    ],
)
def test_parse_liebert_temp_air(string_table: list[StringTable], result: ParsedSection) -> None:
    parsed = parse_liebert_temp_air(string_table)
    assert parsed == result


@pytest.mark.parametrize(
    "section, extra_section, result",
    [
        (
            PARSED_SECTION,
            PARSED_EXTRA_SECTION,
            [Service(item="Return")],
        )
    ],
)
def test_discover_liebert_temp_air(
    section: ParsedSection, extra_section: SystemSection, result: DiscoveryResult
) -> None:
    discovered = list(discover_liebert_temp_air(section, extra_section))
    assert discovered == result


@pytest.mark.parametrize(
    "item, params, section, extra_section, result",
    [
        (
            "Return",
            PARAMETERS,
            PARSED_SECTION,
            PARSED_EXTRA_SECTION,
            [
                Metric(name="temp", value=42.0, levels=(50.0, 55.0)),
                Result(state=State.OK, summary="Temperature: 42.0 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
        ),
        (
            # Item 'Some made-up' is not discovered in the discovery function. However, it is tested in this check function
            # in order to test whether the check handles the item correctly when it changes its status from 'on' to
            # 'standby'.
            "Some made-up",
            PARAMETERS,
            PARSED_SECTION,
            PARSED_EXTRA_SECTION,
            [
                Result(state=State.OK, summary="Unit is in standby (unavailable)"),
            ],
        ),
    ],
)
def test_check_liebert_temp_air(
    item: str,
    params: TempParamDict,
    section: ParsedSection,
    extra_section: SystemSection,
    result: CheckResult,
) -> None:
    checked = list(_check_liebert_temp_air(item, params, section, extra_section, {}))
    assert checked == result


def test_check_liebert_temp_air_trend() -> None:
    value_store: dict[str, typing.Any] = {}
    params: TempParamDict = PARAMETERS.copy()
    trend_compute: TrendComputeDict = {"period": 60}
    params["trend_compute"] = trend_compute

    def _get_check_result(temp: str) -> CheckResult:
        return list(
            _check_liebert_temp_air(
                item="Return",
                params=params,
                section_liebert_temp_air={
                    "Return Air Temperature": (temp, "deg F"),
                },
                section_liebert_system=PARSED_EXTRA_SECTION,
                value_store=value_store,
            )
        )

    with time_machine.travel(datetime.datetime.fromisoformat("1970-01-01 01:00:00Z")):
        with pytest.raises(IgnoreResultsError):
            _get_check_result("20.0")  # -6.66 °C

    with time_machine.travel(datetime.datetime.fromisoformat("1970-01-01 02:00:00Z")):
        with pytest.raises(IgnoreResultsError):
            _get_check_result("30.0")  # -1.11 °C

    with time_machine.travel(datetime.datetime.fromisoformat("1970-01-01 03:00:00Z")):
        result = _get_check_result("40.0")  # 4.44  °C

    assert result == [
        Metric("temp", 4.444444444444445, levels=(50.0, 55.0)),
        Result(state=State.CRIT, summary="Temperature: 4.4 °C (warn/crit below 10 °C/15 °C)"),
        Result(state=State.OK, summary="Temperature trend: +5.6 °C per 60 min"),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (used user levels)",
        ),
    ]
