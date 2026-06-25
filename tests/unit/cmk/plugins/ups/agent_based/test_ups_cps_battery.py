#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.ups.agent_based.ups_cps_battery import (
    check_ups_cps_battery,
    discover_ups_cps_battery,
    parse_ups_cps_battery,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["73", "41", "528000"]], [Service()]),
        ([], []),
    ],
)
def test_discover_ups_cps_battery(
    string_table: StringTable, expected_discoveries: list[Service]
) -> None:
    assert (
        list(discover_ups_cps_battery(parse_ups_cps_battery(string_table))) == expected_discoveries
    )


@pytest.mark.parametrize(
    "params, string_table, expected_results",
    [
        (
            {"capacity": (95, 90)},
            [["73", "41", "528000"]],
            [
                Result(state=State.CRIT, summary="Capacity at 73% (warn/crit at 95/90%)"),
                Result(state=State.OK, summary="88 minutes remaining on battery"),
            ],
        ),
    ],
)
def test_check_ups_cps_battery(
    params: Mapping[str, object], string_table: StringTable, expected_results: list[Result]
) -> None:
    assert (
        list(check_ups_cps_battery(params, parse_ups_cps_battery(string_table))) == expected_results
    )
