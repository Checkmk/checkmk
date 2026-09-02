#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.legacy_checks.intel_true_scale_chassis_temp import (
    check_intel_true_scale_chassis_temp,
    discover_intel_true_scale_chassis_temp,
    parse_intel_true_scale_chassis_temp,
)


@pytest.mark.parametrize(
    "string_table, expected_discovery",
    [
        pytest.param([["1", "0"]], [Service()], id="sensor_present"),
        pytest.param([["6", "0"]], [], id="no_sensor_is_not_discovered"),
        pytest.param([], [], id="empty_section"),
    ],
)
def test_discover_intel_true_scale_chassis_temp(
    string_table: StringTable, expected_discovery: list[Service]
) -> None:
    assert (
        list(
            discover_intel_true_scale_chassis_temp(
                parse_intel_true_scale_chassis_temp(string_table)
            )
        )
        == expected_discovery
    )


@pytest.mark.parametrize(
    "status, expected_result",
    [
        pytest.param(
            "1",
            Result(state=State.OK, summary="Status: normal, Warning configuration: unspecified"),
            id="normal",
        ),
        pytest.param(
            "2",
            Result(state=State.WARN, summary="Status: high, Warning configuration: unspecified"),
            id="high",
        ),
        pytest.param(
            "3",
            Result(
                state=State.CRIT,
                summary="Status: excessively high, Warning configuration: unspecified",
            ),
            id="excessively_high",
        ),
        pytest.param(
            "4",
            Result(state=State.WARN, summary="Status: low, Warning configuration: unspecified"),
            id="low",
        ),
        pytest.param(
            "5",
            Result(
                state=State.CRIT,
                summary="Status: excessively low, Warning configuration: unspecified",
            ),
            id="excessively_low",
        ),
        pytest.param(
            "6",
            Result(
                state=State.UNKNOWN, summary="Status: no sensor, Warning configuration: unspecified"
            ),
            id="no_sensor",
        ),
        pytest.param(
            "7",
            Result(
                state=State.UNKNOWN, summary="Status: unknown, Warning configuration: unspecified"
            ),
            id="unknown",
        ),
    ],
)
def test_check_intel_true_scale_chassis_temp_status(status: str, expected_result: Result) -> None:
    assert list(
        check_intel_true_scale_chassis_temp(parse_intel_true_scale_chassis_temp([[status, "0"]]))
    ) == [expected_result]


@pytest.mark.parametrize(
    "warn_config, expected_readable",
    [
        pytest.param("0", "unspecified", id="unspecified"),
        pytest.param("1", "heed warning", id="heed_warning"),
        pytest.param("2", "ignore warning", id="ignore_warning"),
        pytest.param("3", "no warning feature", id="no_warning_feature"),
    ],
)
def test_check_intel_true_scale_chassis_temp_warning_configuration(
    warn_config: str, expected_readable: str
) -> None:
    assert list(
        check_intel_true_scale_chassis_temp(
            parse_intel_true_scale_chassis_temp([["1", warn_config]])
        )
    ) == [
        Result(
            state=State.OK,
            summary=f"Status: normal, Warning configuration: {expected_readable}",
        )
    ]
