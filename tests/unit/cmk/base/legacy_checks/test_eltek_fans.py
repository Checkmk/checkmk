#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

from collections.abc import Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.eltek_fans import (
    check_eltek_fans,
    discover_eltek_fans,
    parse_eltek_fans,
)


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        # Test data from dataset - no fans discovered (all values are 0)
        ([["1", "", ""]], []),
        # Test data with working fans
        ([["1", "50", "75"], ["2", "0", "45"]], [("1/1", {}), ("2/1", {}), ("2/2", {})]),
        # Test data with only one fan working per unit
        ([["3", "60", "0"], ["4", "0", "80"]], [("1/3", {}), ("2/4", {})]),
    ],
)
def test_discover_eltek_fans(info: StringTable, expected_discoveries: Sequence[tuple]) -> None:
    """Test discovery function for eltek_fans check."""
    parsed = parse_eltek_fans(info)
    result = list(discover_eltek_fans(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, info, expected_results",
    [
        # Test normal operation within limits
        ("1/1", {"levels": (90.0, 95.0)}, [["1", "50", "75"]], (0, "50.0% of max RPM")),
        # Test warning condition
        (
            "1/1",
            {"levels": (40.0, 50.0)},
            [["1", "45", "75"]],
            (1, "45.0% of max RPM (warn/crit at 40.0%/50.0%)"),
        ),
        # Test critical condition
        (
            "2/1",
            {"levels": (70.0, 80.0)},
            [["1", "50", "85"]],
            (2, "85.0% of max RPM (warn/crit at 70.0%/80.0%)"),
        ),
        # Test lower level warning (NOTE: The function uses wrong logic - it checks against main levels, not levels_lower)
        (
            "1/1",
            {"levels": (90.0, 95.0), "levels_lower": (30.0, 20.0)},
            [["1", "25", "75"]],
            (2, "25.0% of max RPM (warn/crit below 90.0%/95.0%)"),
        ),
        # Test lower level critical (FIXME: The function uses wrong logic - it checks against main levels, not levels_lower)
        (
            "1/1",
            {"levels": (90.0, 95.0), "levels_lower": (30.0, 20.0)},
            [["1", "15", "75"]],
            (2, "15.0% of max RPM (warn/crit below 90.0%/95.0%)"),
        ),
        # Test item not found
        ("1/99", {"levels": (90.0, 95.0)}, [["1", "50", "75"]], None),
    ],
)
def test_check_eltek_fans(
    item: str, params: dict[str, Any], info: list[list[str]], expected_results: Any
) -> None:
    """Test check function for eltek_fans check."""
    parsed = parse_eltek_fans(info)
    result = check_eltek_fans(item, params, parsed)
    assert result == expected_results
