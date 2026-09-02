#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.legacy_checks.intel_true_scale_chassis_temp import (
    check_intel_true_scale_chassis_temp,
    discover_intel_true_scale_chassis_temp,
    parse_intel_true_scale_chassis_temp,
)


@pytest.mark.parametrize(
    "string_table, expected_discovery",
    [
        pytest.param([["1", "0"]], [(None, None)], id="sensor_present"),
        pytest.param([["6", "0"]], [], id="no_sensor_is_not_discovered"),
        pytest.param([], [], id="empty_section"),
    ],
)
def test_discover_intel_true_scale_chassis_temp(
    string_table: StringTable, expected_discovery: list[tuple[None, None]]
) -> None:
    assert (
        discover_intel_true_scale_chassis_temp(parse_intel_true_scale_chassis_temp(string_table))
        == expected_discovery
    )


@pytest.mark.parametrize(
    "status, expected_result",
    [
        pytest.param("1", (0, "Status: normal, Warning configuration: unspecified"), id="normal"),
        pytest.param("2", (1, "Status: high, Warning configuration: unspecified"), id="high"),
        pytest.param(
            "3",
            (2, "Status: excessively high, Warning configuration: unspecified"),
            id="excessively_high",
        ),
        pytest.param("4", (1, "Status: low, Warning configuration: unspecified"), id="low"),
        pytest.param(
            "5",
            (2, "Status: excessively low, Warning configuration: unspecified"),
            id="excessively_low",
        ),
        pytest.param(
            "6", (3, "Status: no sensor, Warning configuration: unspecified"), id="no_sensor"
        ),
        pytest.param("7", (3, "Status: unknown, Warning configuration: unspecified"), id="unknown"),
    ],
)
def test_check_intel_true_scale_chassis_temp_status(
    status: str, expected_result: tuple[int, str]
) -> None:
    assert (
        check_intel_true_scale_chassis_temp(
            None, None, parse_intel_true_scale_chassis_temp([[status, "0"]])
        )
        == expected_result
    )


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
    assert check_intel_true_scale_chassis_temp(
        None, None, parse_intel_true_scale_chassis_temp([["1", warn_config]])
    ) == (0, f"Status: normal, Warning configuration: {expected_readable}")
