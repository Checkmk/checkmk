#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Sequence

import pytest

from cmk.base.legacy_checks.emc_isilon_cpu import (
    check_emc_isilon_cpu_utilization,
    discover_emc_isilon_cpu_utilization,
    parse_emc_isilon_cpu,
)

# Test data representing typical EMC Isilon CPU utilization information


@pytest.fixture(name="string_table_normal")
def fixture_string_table_normal() -> Sequence[Sequence[str]]:
    """Standard EMC Isilon CPU utilization data."""
    return [["123", "234", "231", "567"]]


@pytest.fixture(name="string_table_low_usage")
def fixture_string_table_low_usage() -> Sequence[Sequence[str]]:
    """EMC Isilon CPU with low utilization."""
    return [["50", "30", "100", "20"]]


@pytest.fixture(name="string_table_high_usage")
def fixture_string_table_high_usage() -> Sequence[Sequence[str]]:
    """EMC Isilon CPU with high utilization that should trigger warnings."""
    return [["800", "200", "500", "300"]]


@pytest.fixture(name="string_table_empty")
def fixture_string_table_empty() -> Sequence[Sequence[str]]:
    """Empty string table."""
    return []


@pytest.fixture(name="string_table_zero_values")
def fixture_string_table_zero_values() -> Sequence[Sequence[str]]:
    """EMC Isilon CPU with zero values."""
    return [["0", "0", "0", "0"]]


@pytest.fixture(name="string_table_multiple_lines")
def fixture_string_table_multiple_lines() -> Sequence[Sequence[str]]:
    """Multiple lines of CPU data (though only first should be processed)."""
    return [
        ["123", "234", "231", "567"],
        ["200", "100", "150", "300"],
    ]


def test_parse_emc_isilon_cpu_normal(string_table_normal: list[list[str]]) -> None:
    """Test parsing of normal EMC Isilon CPU data."""
    result = parse_emc_isilon_cpu(string_table_normal)
    assert result == [["123", "234", "231", "567"]]


def test_parse_emc_isilon_cpu_empty(string_table_empty: list[list[str]]) -> None:
    """Test parsing of empty string table."""
    result = parse_emc_isilon_cpu(string_table_empty)
    assert result is None


def test_parse_emc_isilon_cpu_multiple_lines(
    string_table_multiple_lines: list[list[str]],
) -> None:
    """Test parsing of multiple lines."""
    result = parse_emc_isilon_cpu(string_table_multiple_lines)
    assert result == [
        ["123", "234", "231", "567"],
        ["200", "100", "150", "300"],
    ]


def test_discover_emc_isilon_cpu_utilization(string_table_normal: list[list[str]]) -> None:
    """Test discovery of EMC Isilon CPU utilization."""
    parsed = parse_emc_isilon_cpu(string_table_normal)
    result = list(discover_emc_isilon_cpu_utilization(parsed))
    assert result == [(None, {})]


def test_discover_emc_isilon_cpu_utilization_empty(
    string_table_empty: list[list[str]],
) -> None:
    """Test discovery with empty data."""
    parsed = parse_emc_isilon_cpu(string_table_empty)
    result = list(discover_emc_isilon_cpu_utilization(parsed))
    assert result == [(None, {})]


def test_check_emc_isilon_cpu_utilization_normal(
    string_table_normal: list[list[str]],
) -> None:
    """Test check function with normal CPU utilization."""
    parsed = parse_emc_isilon_cpu(string_table_normal)
    result = list(check_emc_isilon_cpu_utilization(None, {}, parsed))

    # Should have 4 results: user, system, interrupt, total
    assert len(result) == 4

    # Check user utilization (123 + 234) * 0.1 = 35.7%
    user_result = result[0]
    assert user_result[0] == 0  # OK state
    assert "User: 35.70%" in user_result[1]
    assert user_result[2] == [("user", 35.7, None, None)]

    # Check system utilization 231 * 0.1 = 23.1%
    system_result = result[1]
    assert system_result[0] == 0  # OK state
    assert "System: 23.10%" in system_result[1]
    assert system_result[2] == [("system", 23.1, None, None)]

    # Check interrupt utilization 567 * 0.1 = 56.7%
    interrupt_result = result[2]
    assert interrupt_result[0] == 0  # OK state
    assert "Interrupt: 56.70%" in interrupt_result[1]
    assert interrupt_result[2] == [("interrupt", 56.7, None, None)]

    # Check total utilization 35.7 + 23.1 + 56.7 = 115.5%
    total_result = result[3]
    assert total_result[0] == 0  # OK state
    assert "Total: 115.50%" in total_result[1]


def test_check_emc_isilon_cpu_utilization_low_usage(
    string_table_low_usage: list[list[str]],
) -> None:
    """Test check function with low CPU utilization."""
    parsed = parse_emc_isilon_cpu(string_table_low_usage)
    result = list(check_emc_isilon_cpu_utilization(None, {}, parsed))

    assert len(result) == 4

    # Check user utilization (50 + 30) * 0.1 = 8.0%
    user_result = result[0]
    assert user_result[0] == 0  # OK state
    assert "User: 8.00%" in user_result[1]

    # Check system utilization 100 * 0.1 = 10.0%
    system_result = result[1]
    assert system_result[0] == 0  # OK state
    assert "System: 10.00%" in system_result[1]

    # Check interrupt utilization 20 * 0.1 = 2.0%
    interrupt_result = result[2]
    assert interrupt_result[0] == 0  # OK state
    assert "Interrupt: 2.00%" in interrupt_result[1]

    # Check total utilization 8.0 + 10.0 + 2.0 = 20.0%
    total_result = result[3]
    assert total_result[0] == 0  # OK state
    assert "Total: 20.00%" in total_result[1]


def test_check_emc_isilon_cpu_utilization_with_thresholds() -> None:
    """Test check function with custom threshold parameters."""
    string_table = [["800", "200", "500", "300"]]  # High CPU usage
    parsed = parse_emc_isilon_cpu(string_table)

    # Dictionary-style parameters with util thresholds
    params = {"util": (80.0, 90.0)}  # warn at 80%, crit at 90%

    result = list(check_emc_isilon_cpu_utilization(None, params, parsed))

    assert len(result) == 4

    # Check user utilization (800 + 200) * 0.1 = 100.0%
    user_result = result[0]
    assert user_result[0] == 0  # OK state (no thresholds for individual components)
    assert "User: 100.00%" in user_result[1]

    # Check system utilization 500 * 0.1 = 50.0%
    system_result = result[1]
    assert system_result[0] == 0  # OK state
    assert "System: 50.00%" in system_result[1]

    # Check interrupt utilization 300 * 0.1 = 30.0%
    interrupt_result = result[2]
    assert interrupt_result[0] == 0  # OK state
    assert "Interrupt: 30.00%" in interrupt_result[1]

    # Check total utilization 100.0 + 50.0 + 30.0 = 180.0% (exceeds thresholds)
    total_result = result[3]
    assert total_result[0] == 2  # CRITICAL state (> 90%)
    assert "Total: 180.00%" in total_result[1]


def test_check_emc_isilon_cpu_utilization_legacy_params() -> None:
    """Test check function with legacy tuple-style parameters."""
    string_table = [["600", "100", "200", "150"]]  # Moderate CPU usage
    parsed = parse_emc_isilon_cpu(string_table)

    # Legacy tuple-style parameters
    params = (70.0, 85.0)  # warn at 70%, crit at 85%

    result = list(check_emc_isilon_cpu_utilization(None, params, parsed))

    assert len(result) == 4

    # Check total utilization (600 + 100) * 0.1 + 200 * 0.1 + 150 * 0.1 = 105.0%
    total_result = result[3]
    assert total_result[0] == 2  # CRITICAL state (> 85%)
    assert "Total: 105.00%" in total_result[1]


def test_check_emc_isilon_cpu_utilization_zero_values(
    string_table_zero_values: list[list[str]],
) -> None:
    """Test check function with zero CPU utilization."""
    parsed = parse_emc_isilon_cpu(string_table_zero_values)
    result = list(check_emc_isilon_cpu_utilization(None, {}, parsed))

    assert len(result) == 4

    # All values should be 0%
    for i, component in enumerate(["User", "System", "Interrupt", "Total"]):
        component_result = result[i]
        assert component_result[0] == 0  # OK state
        assert f"{component}: 0%" in component_result[1]


def test_check_emc_isilon_cpu_utilization_multiple_lines(
    string_table_multiple_lines: list[list[str]],
) -> None:
    """Test check function with multiple lines (processes all lines)."""
    parsed = parse_emc_isilon_cpu(string_table_multiple_lines)
    result = list(check_emc_isilon_cpu_utilization(None, {}, parsed))

    # Should process both lines and have 8 results (4 per line)
    assert len(result) == 8

    # Check values match first line: ["123", "234", "231", "567"]
    user_result_1 = result[0]
    assert "User: 35.70%" in user_result_1[1]  # (123 + 234) * 0.1

    system_result_1 = result[1]
    assert "System: 23.10%" in system_result_1[1]  # 231 * 0.1

    interrupt_result_1 = result[2]
    assert "Interrupt: 56.70%" in interrupt_result_1[1]  # 567 * 0.1

    total_result_1 = result[3]
    assert "Total: 115.50%" in total_result_1[1]  # 35.7 + 23.1 + 56.7

    # Check values match second line: ["200", "100", "150", "300"]
    user_result_2 = result[4]
    assert "User: 30.00%" in user_result_2[1]  # (200 + 100) * 0.1

    system_result_2 = result[5]
    assert "System: 15.00%" in system_result_2[1]  # 150 * 0.1

    interrupt_result_2 = result[6]
    assert "Interrupt: 30.00%" in interrupt_result_2[1]  # 300 * 0.1

    total_result_2 = result[7]
    assert "Total: 75.00%" in total_result_2[1]  # 30.0 + 15.0 + 30.0


def test_check_emc_isilon_cpu_utilization_empty_data() -> None:
    assert not list(check_emc_isilon_cpu_utilization(None, {}, []))


def test_check_emc_isilon_cpu_utilization_warning_threshold() -> None:
    """Test check function triggering warning threshold."""
    string_table = [["400", "100", "300", "200"]]  # Total = 100%
    parsed = parse_emc_isilon_cpu(string_table)

    params = {"util": (80.0, 120.0)}  # warn at 80%, crit at 120%

    result = list(check_emc_isilon_cpu_utilization(None, params, parsed))

    # Check total utilization: (400 + 100) * 0.1 + 300 * 0.1 + 200 * 0.1 = 100.0%
    total_result = result[3]
    assert total_result[0] == 1  # WARNING state (between 80% and 120%)
    assert "Total: 100.00%" in total_result[1]


def test_check_emc_isilon_cpu_utilization_performance_data() -> None:
    """Test that performance data is correctly included."""
    string_table = [["100", "50", "75", "25"]]
    parsed = parse_emc_isilon_cpu(string_table)
    result = list(check_emc_isilon_cpu_utilization(None, {}, parsed))

    # Check that all individual metrics have performance data
    user_result = result[0]
    assert user_result[2] == [("user", 15.0, None, None)]  # (100+50)*0.1

    system_result = result[1]
    assert system_result[2] == [("system", 7.5, None, None)]  # 75*0.1

    interrupt_result = result[2]
    assert interrupt_result[2] == [("interrupt", 2.5, None, None)]  # 25*0.1

    # Total should have performance data as well
    # The exact performance data format may vary based on check_levels implementation
