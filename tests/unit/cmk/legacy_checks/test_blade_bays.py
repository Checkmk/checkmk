#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State, StringTable
from cmk.legacy_checks.blade_bays import (
    check_blade_bays,
    discover_blade_bays,
    parse_blade_bays,
)

STRING_TABLE_1 = [
    [
        ["1", "SomeName1", "1", "type1(ignored)", "1", "4W", "6W"],
        ["2", "SomeName2", "0", "type2(ignored)", "A", "5W", "5W"],
    ],
    [
        ["1", "SomeName1", "1", "type3(ignored)", "1", "5W", "5W"],
        ["2", "SomeName3", "1", "type4(ignored)", "B", "5W", "5W"],
        ["2", "SomeName4", "x", "type5(ignored)", "2", "5W", "5W"],
    ],
]


@pytest.mark.parametrize(
    ("string_table", "expected_discoveries"),
    [
        pytest.param(
            STRING_TABLE_1,
            [
                Service(item="PD1 SomeName1"),
                Service(item="PD1 SomeName2"),
                Service(item="PD2 SomeName1"),
                Service(item="PD2 SomeName3"),
            ],
        ),
    ],
)
def test_discover_blade_bays(
    string_table: Sequence[StringTable],
    expected_discoveries: Sequence[Service],
) -> None:
    parsed = parse_blade_bays(string_table)
    result = list(discover_blade_bays(parsed))
    assert sorted(result) == expected_discoveries


@pytest.mark.parametrize(
    ("string_table", "expected_results"),
    [
        pytest.param(
            STRING_TABLE_1,
            {
                "PD1 SomeName1": [
                    Result(state=State.OK, summary="Status: on"),
                    Result(state=State.OK, summary="Type: type1"),
                    Result(state=State.OK, summary="Device status: on(0)"),
                    Result(state=State.OK, summary="Power: 4.0 W"),
                    Metric("power", 4.0),
                    Result(state=State.OK, summary="Max. power: 6 W"),
                    Result(state=State.OK, summary="ID: 1"),
                ],
                "PD1 SomeName2": [
                    Result(state=State.OK, summary="Status: standby"),
                    Result(state=State.OK, summary="Type: type2"),
                    Result(state=State.OK, summary="Device status: standby(0)"),
                    Result(state=State.OK, summary="Power: 5.0 W"),
                    Metric("power", 5.0),
                    Result(state=State.OK, summary="Max. power: 5 W"),
                    Result(state=State.OK, summary="ID: A"),
                ],
                "PD2 SomeName1": [
                    Result(state=State.OK, summary="Status: on"),
                    Result(state=State.OK, summary="Type: type3"),
                    Result(state=State.OK, summary="Device status: on(0)"),
                    Result(state=State.OK, summary="Power: 5.0 W"),
                    Metric("power", 5.0),
                    Result(state=State.OK, summary="Max. power: 5 W"),
                    Result(state=State.OK, summary="ID: 1"),
                ],
                "PD2 SomeName3": [
                    Result(state=State.OK, summary="Status: on"),
                    Result(state=State.OK, summary="Type: type4"),
                    Result(state=State.OK, summary="Device status: on(0)"),
                    Result(state=State.OK, summary="Power: 5.0 W"),
                    Metric("power", 5.0),
                    Result(state=State.OK, summary="Max. power: 5 W"),
                    Result(state=State.OK, summary="ID: B"),
                ],
            },
        ),
    ],
)
def test_check_blade_bays(
    string_table: Sequence[StringTable], expected_results: Mapping[str, CheckResult]
) -> None:
    parsed = parse_blade_bays(string_table)
    services = list(discover_blade_bays(parsed))
    result = {
        service.item: list(check_blade_bays(service.item, parsed))
        for service in services
        if service.item is not None
    }
    assert result == expected_results
