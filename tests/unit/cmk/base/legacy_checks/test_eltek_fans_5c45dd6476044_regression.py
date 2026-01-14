#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from typing import Any

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.eltek_fans import (
    check_eltek_fans,
    discover_eltek_fans,
    parse_eltek_fans,
)


@pytest.fixture(name="eltek_fans_regression_data")
def _eltek_fans_regression_data() -> StringTable:
    """Return test data from regression dataset."""
    return [["1", "", ""]]


class TestEltekFansRegression:
    """Test Eltek fans check with regression dataset."""

    def test_parse_function(self, eltek_fans_regression_data: StringTable) -> None:
        """Test parse function for Eltek fans."""
        result = parse_eltek_fans(eltek_fans_regression_data)
        assert result == [["1", "", ""]]

    def test_discovery_no_fans(self, eltek_fans_regression_data: StringTable) -> None:
        """Test discovery function with no working fans."""
        parsed = parse_eltek_fans(eltek_fans_regression_data)
        result = list(discover_eltek_fans(parsed))
        # No fans discovered since both fan speed values are empty
        assert result == []

    def test_check_function_empty_string_error(
        self, eltek_fans_regression_data: StringTable
    ) -> None:
        """Test check function fails with empty strings (demonstrates bug in legacy check)."""
        parsed = parse_eltek_fans(eltek_fans_regression_data)
        # The legacy check function fails when trying to convert empty strings to float
        with pytest.raises(ValueError, match="could not convert string to float"):
            check_eltek_fans("1/1", {"levels": (90.0, 95.0)}, parsed)

    def test_check_function_empty_string_error_fan2(
        self, eltek_fans_regression_data: StringTable
    ) -> None:
        """Test check function fails with empty strings for fan 2."""
        parsed = parse_eltek_fans(eltek_fans_regression_data)
        # The legacy check function fails when trying to convert empty strings to float
        with pytest.raises(ValueError, match="could not convert string to float"):
            check_eltek_fans("2/1", {"levels": (90.0, 95.0)}, parsed)


@pytest.mark.parametrize(
    "test_data, expected_discoveries",
    [
        # Regression case: empty fan values
        ([["1", "", ""]], []),
        # Working fans for comparison
        ([["1", "50", "75"]], [("1/1", {}), ("2/1", {})]),
        ([["2", "0", "45"]], [("2/2", {})]),
        # Multiple units
        ([["1", "60", "0"], ["2", "0", "80"]], [("1/1", {}), ("2/2", {})]),
    ],
)
def test_eltek_fans_discovery_scenarios(
    test_data: StringTable, expected_discoveries: list[tuple[str, dict[str, Any]]]
) -> None:
    """Test discovery function with various scenarios."""
    parsed = parse_eltek_fans(test_data)
    result = list(discover_eltek_fans(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "test_data, item, params, expected_result",
    [
        # Working fan scenarios for validation
        ([["1", "50", "75"]], "1/1", {"levels": (90.0, 95.0)}, (0, "50.0% of max RPM")),
        ([["1", "50", "75"]], "2/1", {"levels": (90.0, 95.0)}, (0, "75.0% of max RPM")),
        # Warning threshold
        (
            [["1", "92", "75"]],
            "1/1",
            {"levels": (90.0, 95.0)},
            (1, "92.0% of max RPM (warn/crit at 90.0%/95.0%)"),
        ),
        # Critical threshold
        (
            [["1", "96", "75"]],
            "1/1",
            {"levels": (90.0, 95.0)},
            (2, "96.0% of max RPM (warn/crit at 90.0%/95.0%)"),
        ),
    ],
)
def test_eltek_fans_check_scenarios(
    test_data: StringTable, item: str, params: dict[str, Any], expected_result: Any
) -> None:
    """Test check function with various scenarios."""
    parsed = parse_eltek_fans(test_data)
    result = check_eltek_fans(item, params, parsed)
    assert result == expected_result


def test_eltek_fans_regression_empty_strings() -> None:
    """Test that regression dataset with empty strings causes ValueError."""
    test_data = [["1", "", ""]]
    parsed = parse_eltek_fans(test_data)
    # The legacy check function fails when trying to convert empty strings to float
    with pytest.raises(ValueError, match="could not convert string to float"):
        check_eltek_fans("1/1", {"levels": (90.0, 95.0)}, parsed)

    with pytest.raises(ValueError, match="could not convert string to float"):
        check_eltek_fans("2/1", {"levels": (90.0, 95.0)}, parsed)


def test_eltek_fans_empty_string_handling() -> None:
    """Test that empty strings are handled correctly in discovery."""
    test_data = [["1", "", ""], ["2", "0", ""], ["3", "", "50"]]
    parsed = parse_eltek_fans(test_data)
    result = list(discover_eltek_fans(parsed))
    # Only fan 2/3 should be discovered since it has value 50
    assert result == [("2/3", {})]


def test_eltek_fans_zero_value_handling() -> None:
    """Test that zero values are correctly excluded from discovery."""
    test_data = [["1", "0", "0"], ["2", "45", "0"], ["3", "0", "60"]]
    parsed = parse_eltek_fans(test_data)
    result = list(discover_eltek_fans(parsed))
    # Only fans with non-zero values should be discovered
    assert sorted(result) == sorted([("1/2", {}), ("2/3", {})])


def test_eltek_fans_lower_levels() -> None:
    """Test check function with lower level thresholds."""
    test_data = [["1", "15", "75"]]
    parsed = parse_eltek_fans(test_data)
    params = {"levels": (90.0, 95.0), "levels_lower": (30.0, 20.0)}
    result = check_eltek_fans("1/1", params, parsed)
    # Fan at 15% should trigger critical since it's below 20%
    assert result == (2, "15.0% of max RPM (warn/crit below 90.0%/95.0%)")


def test_eltek_fans_lower_levels_warning() -> None:
    """Test check function with lower level warning threshold (bug in legacy check)."""
    test_data = [["1", "25", "75"]]
    parsed = parse_eltek_fans(test_data)
    params = {"levels": (90.0, 95.0), "levels_lower": (30.0, 20.0)}
    result = check_eltek_fans("1/1", params, parsed)
    # NOTE: Legacy check has a bug - it compares against main levels (90.0, 95.0) instead of levels_lower (30.0, 20.0)
    # Fan at 25% should trigger critical since it's below 90% (main warn level)
    assert result == (2, "25.0% of max RPM (warn/crit below 90.0%/95.0%)")
