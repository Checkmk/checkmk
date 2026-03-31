#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State, StringTable
from cmk.plugins.blade.agent_based import blade_bx_temp
from cmk.plugins.blade.agent_based.blade_bx_temp import (
    check_blade_bx_temp,
    discover_blade_bx_temp,
    parse_blade_bx_temp,
)
from cmk.plugins.lib.temperature import TempParamType

STRING_TABLE_1 = [
    # _index, status, descr, level_warn, level_crit, temp, crit_react
    ["1", "3", "Descr1", "70", "85", "32", "2"],
    ["2", "3", "Descr2", "70", "85", "75", "2"],
    ["3", "3", "Descr3", "70", "85", "90", "2"],
    ["4", "7", "Descr4", "70", "85", "32", "2"],  # status: not available
    ["5", "4", "Descr5", "70", "85", "32", "2"],  # status: sensor-failed
    ["6", "3", "Descr6", "70", "85", "32", "1"],  # crit_react != 2
]


@pytest.fixture
def empty_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    store = dict[str, object]()
    monkeypatch.setattr(blade_bx_temp, "get_value_store", lambda: store)


@pytest.mark.parametrize(
    ("string_table", "expected_discoveries"),
    [
        pytest.param(
            STRING_TABLE_1,
            [
                Service(item="Descr1"),
                Service(item="Descr2"),
                Service(item="Descr3"),
                Service(item="Descr5"),
                Service(item="Descr6"),
            ],
        ),
    ],
)
def test_discover_blade_bx_temp(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    parsed = parse_blade_bx_temp(string_table)
    result = list(discover_blade_bx_temp(parsed))
    assert sorted(result) == expected_discoveries


@pytest.mark.parametrize(
    ("string_table", "params", "expected_results"),
    [
        pytest.param(
            STRING_TABLE_1,
            None,
            {
                "Descr1": [
                    Metric("temp", 32.0, levels=(70.0, 85.0)),
                    Result(
                        state=State.OK,
                        summary="Temperature: 32.0 °C",
                    ),
                    Result(
                        state=State.OK,
                        notice="Configuration: prefer user levels over device levels (used device levels)",
                    ),
                ],
                "Descr2": [
                    Metric("temp", 75.0, levels=(70.0, 85.0)),
                    Result(
                        state=State.WARN,
                        summary="Temperature: 75.0 °C (warn/crit at 70.0 °C/85.0 °C)",
                    ),
                    Result(
                        state=State.OK,
                        notice="Configuration: prefer user levels over device levels (used device levels)",
                    ),
                ],
                "Descr3": [
                    Metric("temp", 90.0, levels=(70.0, 85.0)),
                    Result(
                        state=State.CRIT,
                        summary="Temperature: 90.0 °C (warn/crit at 70.0 °C/85.0 °C)",
                    ),
                    Result(
                        state=State.OK,
                        notice="Configuration: prefer user levels over device levels (used device levels)",
                    ),
                ],
                "Descr5": [
                    Result(
                        state=State.CRIT,
                        summary="Status is sensor-failed",
                    ),
                    Metric("temp", 32.0),
                ],
                "Descr6": [
                    Result(
                        state=State.CRIT,
                        summary="Temperature not present or poweroff",
                    ),
                    Metric("temp", 32.0),
                ],
            },
            id="01_no_params",
        ),
        pytest.param(
            STRING_TABLE_1,
            {"levels": (60, 70)},
            {
                "Descr1": [
                    Metric("temp", 32.0, levels=(60.0, 70.0)),
                    Result(
                        state=State.OK,
                        summary="Temperature: 32.0 °C",
                    ),
                    Result(
                        state=State.OK,
                        notice="Configuration: prefer user levels over device levels (used user levels)",
                    ),
                ],
                "Descr2": [
                    Metric("temp", 75.0, levels=(60.0, 70.0)),
                    Result(
                        state=State.CRIT, summary="Temperature: 75.0 °C (warn/crit at 60 °C/70 °C)"
                    ),
                    Result(
                        state=State.OK,
                        notice="Configuration: prefer user levels over device levels (used user levels)",
                    ),
                ],
                "Descr3": [
                    Metric("temp", 90.0, levels=(60.0, 70.0)),
                    Result(
                        state=State.CRIT, summary="Temperature: 90.0 °C (warn/crit at 60 °C/70 °C)"
                    ),
                    Result(
                        state=State.OK,
                        notice="Configuration: prefer user levels over device levels (used user levels)",
                    ),
                ],
                "Descr5": [
                    Result(
                        state=State.CRIT,
                        summary="Status is sensor-failed",
                    ),
                    Metric("temp", 32.0),
                ],
                "Descr6": [
                    Result(
                        state=State.CRIT,
                        summary="Temperature not present or poweroff",
                    ),
                    Metric("temp", 32.0),
                ],
            },
            id="02_with_levels",
        ),
        pytest.param(
            STRING_TABLE_1,
            {"levels_lower": (40, 30)},
            {
                "Descr1": [
                    Metric("temp", 32.0, levels=(70.0, 85.0)),
                    Result(
                        state=State.WARN,
                        summary="Temperature: 32.0 °C (device warn/crit at 70/85 °C)",
                    ),
                    Result(
                        state=State.OK,
                        notice="Configuration: prefer device levels over user levels (used device levels)",
                    ),
                ],
                "Descr2": [
                    Metric("temp", 75.0, levels=(70.0, 85.0)),
                    Result(
                        state=State.WARN,
                        summary="Temperature: 75.0 °C (warn/crit at 70.0 °C/85.0 °C)",
                    ),
                    Result(
                        state=State.OK,
                        notice="Configuration: prefer device levels over user levels (used device levels)",
                    ),
                ],
                "Descr3": [
                    Metric("temp", 90.0, levels=(70.0, 85.0)),
                    Result(
                        state=State.CRIT,
                        summary="Temperature: 90.0 °C (warn/crit at 70.0 °C/85.0 °C)",
                    ),
                    Result(
                        state=State.OK,
                        notice="Configuration: prefer device levels over user levels (used device levels)",
                    ),
                ],
                "Descr5": [
                    Result(
                        state=State.CRIT,
                        summary="Status is sensor-failed",
                    ),
                    Metric("temp", 32.0),
                ],
                "Descr6": [
                    Result(
                        state=State.CRIT,
                        summary="Temperature not present or poweroff",
                    ),
                    Metric("temp", 32.0),
                ],
            },
            id="03_with_levels_lower",
            marks=pytest.mark.xfail(reason="CMK-33436"),
        ),
    ],
)
def test_check_blade_bx_temp(
    empty_value_store: None,
    string_table: StringTable,
    params: None | TempParamType,
    expected_results: Mapping[str, CheckResult],
) -> None:
    parsed = parse_blade_bx_temp(string_table)
    services = list(discover_blade_bx_temp(parsed))
    result = {
        service.item: list(check_blade_bx_temp(service.item, params, parsed))
        for service in services
        if service.item is not None
    }
    assert result == expected_results
