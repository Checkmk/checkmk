#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.ups.agent_based.ups_eaton_enviroment import (
    check_ups_eaton_enviroment,
    discover_ups_eaton_enviroment,
    parse_ups_eaton_enviroment,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["1", "40", "3"]], [Service()]),
        ([], []),
    ],
)
def test_discover_ups_eaton_enviroment(
    string_table: StringTable, expected_discoveries: list[Service]
) -> None:
    parsed = parse_ups_eaton_enviroment(string_table)
    assert list(discover_ups_eaton_enviroment(parsed)) == expected_discoveries


@pytest.mark.parametrize(
    "params, string_table, expected_results",
    [
        (
            {"humidity": (65, 80), "remote_temp": (40, 50), "temp": (40, 50)},
            [["1", "40", "3"]],
            [
                Result(state=State.OK, summary="Temperature: 1.0 °C"),
                Metric("temp", 1.0, levels=(40.0, 50.0)),
                Result(
                    state=State.WARN,
                    summary="Remote-Temperature: 40.0 °C (warn/crit at 40.0 °C/50.0 °C)",
                ),
                Metric("remote_temp", 40.0, levels=(40.0, 50.0)),
                Result(state=State.OK, summary="Humidity: 3.0%"),
                Metric("humidity", 3.0, levels=(65.0, 80.0)),
            ],
        ),
    ],
)
def test_check_ups_eaton_enviroment(
    params: Mapping[str, object], string_table: StringTable, expected_results: list[object]
) -> None:
    parsed = parse_ups_eaton_enviroment(string_table)
    assert list(check_ups_eaton_enviroment(params, parsed)) == expected_results
