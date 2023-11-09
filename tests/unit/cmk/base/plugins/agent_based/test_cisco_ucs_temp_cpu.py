#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence

import pytest

from cmk.base.legacy_checks.cisco_ucs_temp_cpu import (
    check_cisco_ucs_temp_cpu,
    inventory_cisco_ucs_temp_cpu,
)
from cmk.base.plugins.agent_based.cisco_ucs_temp_cpu import parse_cisco_ucs_temp_cpu
from cmk.base.plugins.agent_based.utils.temperature import TempParamType as TempParamType


@pytest.fixture(name="section", scope="module")
def fixture_section() -> dict[str, int]:
    return parse_cisco_ucs_temp_cpu(
        [
            ["sys/rack-unit-1/board/cpu-1/env-stats", "54"],
            ["sys/rack-unit-1/board/cpu-2/env-stats", "57"],
        ]
    )


def test_inventory_cisco_ucs_temp_cpu(section: Mapping[str, int]) -> None:
    assert list(inventory_cisco_ucs_temp_cpu(section)) == [("cpu-1", {}), ("cpu-2", {})]


@pytest.mark.parametrize(
    "item, params, expected_result",
    [
        pytest.param(
            "cpu-2",
            {"input_unit": "c", "levels": (75.0, 85.0)},
            (0, "57 °C", [("temp", 57, 75.0, 85.0)]),
            id="OK thresholds",
        ),
        pytest.param(
            "cpu-2",
            {"input_unit": "c", "levels": (20.0, 55.0)},
            (2, "57 °C (warn/crit at 20.0/55.0 °C)", [("temp", 57, 20.0, 55.0)]),
            id="CRIT thresholds",
        ),
    ],
)
def test_check_cisco_ucs_temp_cpu(
    item: str, params: TempParamType, expected_result: Sequence[object], section: Mapping[str, int]
) -> None:
    assert check_cisco_ucs_temp_cpu(item, params, section) == expected_result
