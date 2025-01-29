#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.extreme_vsp_switches_fan import (
    check_vsp_switches_fan,
    discover_vsp_switches_fan,
    parse_vsp_switches_fan,
)

_STRING_TABLE = [
    ["Fan 1", "2", "2", "2564"],
    ["Fan 2", "3", "3", "2312"],
    ["Fan 3", "1", "1", ""],
]


@pytest.mark.parametrize(
    "string_table, expected_discovery_result",
    [
        pytest.param(
            _STRING_TABLE,
            [
                Service(item="Fan 1"),
                Service(item="Fan 2"),
                Service(item="Fan 3"),
            ],
            id="For every fan available, a Service is created.",
        ),
        pytest.param(
            [],
            [],
            id="If the are no fans, no Services are created.",
        ),
    ],
)
def test_discover_vsp_switches_fan(
    string_table: StringTable,
    expected_discovery_result: Sequence[Service],
) -> None:
    assert (
        list(discover_vsp_switches_fan(parse_vsp_switches_fan(string_table)))
        == expected_discovery_result
    )


@pytest.mark.parametrize(
    "string_table, item, expected_check_result",
    [
        pytest.param(
            _STRING_TABLE,
            "Fan 1",
            [
                Result(
                    state=State.OK,
                    summary="Fan status: up - present and supplying power; Fan speed: medium",
                ),
                Result(state=State.OK, summary="Speed: 2564 RPM"),
                Metric("fan", 2564.0, levels=(8000.0, 8400.0)),
            ],
            id="The temperature is below the WARN/CRIT levels, so the check state is OK.",
        ),
        pytest.param(
            _STRING_TABLE,
            "Fan 2",
            [
                Result(
                    state=State.CRIT,
                    summary="Fan status: down - present, but failure indicated; Fan speed: high",
                ),
                Result(state=State.OK, summary="Speed: 2312 RPM"),
                Metric("fan", 2312.0, levels=(8000.0, 8400.0)),
            ],
            id="The temperature is above the WARN, so the check state is WARN.",
        ),
        pytest.param(
            _STRING_TABLE,
            "Fan 3",
            [
                Result(
                    state=State.UNKNOWN,
                    summary="Fan status: unknown - status can not be determined; Fan speed: low",
                )
            ],
            id="The temperature is above the CRIT, so the check state is CRIT.",
        ),
    ],
)
def test_check_vsp_switches_fan(
    string_table: StringTable,
    item: str,
    expected_check_result: Sequence[Result | Metric],
) -> None:
    assert (
        list(
            check_vsp_switches_fan(
                item=item,
                params={"lower": (2000, 1000), "upper": (8000, 8400), "output_metrics": True},
                section=parse_vsp_switches_fan(string_table),
            )
        )
        == expected_check_result
    )
