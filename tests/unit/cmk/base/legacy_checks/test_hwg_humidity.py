#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.check_legacy_includes.hwg import parse_hwg
from cmk.base.legacy_checks.hwg_humidity import check_hwg_humidity, discover_hwg_humidity


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        (
            [["1", "Sensor 215", "1", "23.8", "1"], ["2", "Sensor 216", "1", "34.6", "4"]],
            [("2", {})],
        ),
    ],
)
def test_discover_hwg_humidity(
    info: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for hwg_humidity check."""
    parsed = parse_hwg(info)
    result = list(discover_hwg_humidity(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, info, expected_results",
    [
        (
            "2",
            (0, 0, 60, 70),
            [["1", "Sensor 215", "1", "23.8", "1"], ["2", "Sensor 216", "1", "34.6", "4"]],
            [
                (
                    0,
                    "34.60%",
                    [("humidity", 34.6, 60.0, 70.0, 0.0, 100.0)],
                ),
                (
                    0,
                    "Description: Sensor 216, Status: normal",
                ),
            ],
        ),
    ],
)
def test_check_hwg_humidity(
    item: str, params: Mapping[str, Any], info: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for hwg_humidity check."""
    parsed = parse_hwg(info)
    result = list(check_hwg_humidity(item, params, parsed))
    assert result == expected_results
