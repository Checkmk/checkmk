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
from cmk.base.legacy_checks.hwg_temp import check_hwg_temp, discover_hwg_temp


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        (
            [["1", "Netzwerk-Rack", "1", "23.8", "1"], ["2", "Library-Rack", "1", "23.0", "1"]],
            [("1", {}), ("2", {})],
        ),
    ],
)
def test_discover_hwg_temp(
    info: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for hwg_temp check."""
    parsed = parse_hwg(info)
    result = list(discover_hwg_temp(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, info, expected_results",
    [
        (
            "1",
            {"levels": (30, 35)},
            [["1", "Netzwerk-Rack", "1", "23.8", "1"], ["2", "Library-Rack", "1", "23.0", "1"]],
            [
                (
                    0,
                    "23.8 °C (Description: Netzwerk-Rack, Status: normal)",
                    [("temp", 23.8, 30.0, 35.0)],
                )
            ],
        ),
        (
            "2",
            {"levels": (30, 35)},
            [["1", "Netzwerk-Rack", "1", "23.8", "1"], ["2", "Library-Rack", "1", "23.0", "1"]],
            [
                (
                    0,
                    "23.0 °C (Description: Library-Rack, Status: normal)",
                    [("temp", 23.0, 30.0, 35.0)],
                )
            ],
        ),
    ],
)
def test_check_hwg_temp(
    item: str, params: Mapping[str, Any], info: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for hwg_temp check."""
    parsed = parse_hwg(info)
    result = list(check_hwg_temp(item, params, parsed))
    assert result == expected_results
