#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.collection.agent_based.cisco_ucs_temp_cpu import (
    _check_cisco_ucs_temp_cpu,
    discover_cisco_ucs_temp_cpu,
    parse_cisco_ucs_temp_cpu,
)
from cmk.plugins.lib.temperature import TempParamType as TempParamType


@pytest.fixture(name="section", scope="module")
def fixture_section() -> dict[str, int]:
    return parse_cisco_ucs_temp_cpu(
        [
            ["sys/rack-unit-1/board/cpu-1/env-stats", "54"],
            ["sys/rack-unit-1/board/cpu-2/env-stats", "57"],
        ]
    )


def test_discover_cisco_ucs_temp_cpu(section: Mapping[str, int]) -> None:
    assert list(discover_cisco_ucs_temp_cpu(section)) == [
        Service(item="cpu-1"),
        Service(item="cpu-2"),
    ]


@pytest.mark.parametrize(
    "item, params, expected_result",
    [
        pytest.param(
            "cpu-2",
            {"input_unit": "c", "levels": (75.0, 85.0)},
            [
                Metric("temp", 57.0, levels=(75.0, 85.0)),
                Result(state=State.OK, summary="Temperature: 57 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
            id="OK thresholds",
        ),
        pytest.param(
            "cpu-2",
            {"input_unit": "c", "levels": (20.0, 55.0)},
            [
                Metric("temp", 57.0, levels=(20.0, 55.0)),
                Result(
                    state=State.CRIT, summary="Temperature: 57 °C (warn/crit at 20.0 °C/55.0 °C)"
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
            id="CRIT thresholds",
        ),
    ],
)
def test_check_cisco_ucs_temp_cpu(
    item: str,
    params: TempParamType,
    expected_result: CheckResult,
    section: Mapping[str, int],
) -> None:
    assert list(_check_cisco_ucs_temp_cpu(item, params, section, {})) == expected_result
