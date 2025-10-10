#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping

import pytest

from cmk.base.legacy_checks.cadvisor_cpu import (
    check_cadvisor_cpu,
    discover_cadvisor_cpu,
    parse_cadvisor_cpu,
)


@pytest.fixture
def parsed() -> Mapping[str, float]:
    """Create parsed cAdvisor CPU data using actual parse function."""
    string_table = [
        [
            '{"cpu_user": [{"value": "0.10996819381471273", "labels": {"name": "k8s_coredns_coredns-5c98db65d4-b47gr_kube-system_736910b3-0b55-4c11-8291-f9db987489e3_5"}, "host_selection_label": "name"}], "cpu_system": [{"value": "0.12688637747851422", "labels": {"name": "k8s_coredns_coredns-5c98db65d4-b47gr_kube-system_736910b3-0b55-4c11-8291-f9db987489e3_5"}, "host_selection_label": "name"}]}'
        ]
    ]
    return parse_cadvisor_cpu(string_table)


def test_cadvisor_cpu_discovery(parsed: Mapping[str, float]) -> None:
    """Test cAdvisor CPU discovery function."""
    result = list(discover_cadvisor_cpu(parsed))

    # Should discover exactly one service
    assert len(result) == 1
    assert result[0] == (None, {})


def test_cadvisor_cpu_check(parsed: Mapping[str, float]) -> None:
    """Test cAdvisor CPU check function."""
    result = list(check_cadvisor_cpu(None, {}, parsed))

    # Should have exactly 3 results (user, system, total)
    assert len(result) == 3

    # Check user CPU result
    state, summary, metrics = result[0]
    assert state == 0
    assert summary == "User: 0.11%"
    assert len(metrics) == 1
    assert metrics[0][0] == "user"
    assert abs(metrics[0][1] - 0.10996819381471273) < 1e-10

    # Check system CPU result
    state, summary, metrics = result[1]
    assert state == 0
    assert summary == "System: 0.13%"
    assert len(metrics) == 1
    assert metrics[0][0] == "system"
    assert abs(metrics[0][1] - 0.12688637747851422) < 1e-10

    # Check total CPU result
    state, summary, metrics = result[2]
    assert state == 0
    assert summary == "Total CPU: 0.24%"
    assert len(metrics) == 1
    assert metrics[0][0] == "util"
    # Total should be user + system
    expected_total = 0.10996819381471273 + 0.12688637747851422
    assert abs(metrics[0][1] - expected_total) < 1e-10


def test_cadvisor_cpu_check_with_levels(parsed: Mapping[str, float]) -> None:
    """Test cAdvisor CPU check function with warning/critical levels."""
    params = {"util": (50.0, 80.0)}  # 50% warn, 80% crit

    result = list(check_cadvisor_cpu(None, params, parsed))

    # Should still have exactly 3 results
    assert len(result) == 3

    # All should be OK since total CPU is only ~0.24%
    for state, summary, metrics in result:
        assert state == 0


def test_cadvisor_cpu_discovery_empty_section() -> None:
    """Test cAdvisor CPU discovery function with empty section."""
    result = list(discover_cadvisor_cpu({}))

    # Should not discover any service for empty section
    assert len(result) == 0


def test_cadvisor_cpu_parse_function() -> None:
    """Test cAdvisor CPU parse function with the exact dataset."""
    string_table = [
        [
            '{"cpu_user": [{"value": "0.10996819381471273", "labels": {"name": "k8s_coredns_coredns-5c98db65d4-b47gr_kube-system_736910b3-0b55-4c11-8291-f9db987489e3_5"}, "host_selection_label": "name"}], "cpu_system": [{"value": "0.12688637747851422", "labels": {"name": "k8s_coredns_coredns-5c98db65d4-b47gr_kube-system_736910b3-0b55-4c11-8291-f9db987489e3_5"}, "host_selection_label": "name"}]}'
        ]
    ]

    result = parse_cadvisor_cpu(string_table)

    # Verify parsed structure
    assert "cpu_user" in result
    assert "cpu_system" in result
    assert len(result) == 2

    # Check parsed values
    assert abs(result["cpu_user"] - 0.10996819381471273) < 1e-10
    assert abs(result["cpu_system"] - 0.12688637747851422) < 1e-10


def test_cadvisor_cpu_parse_multiple_entries() -> None:
    """Test cAdvisor CPU parse function skips entries with multiple values."""
    string_table = [
        ['{"cpu_user": [{"value": "0.1"}, {"value": "0.2"}], "cpu_system": [{"value": "0.15"}]}']
    ]

    result = parse_cadvisor_cpu(string_table)

    # Should only include cpu_system (single entry), not cpu_user (multiple entries)
    assert "cpu_system" in result
    assert "cpu_user" not in result
    assert result["cpu_system"] == 0.15


def test_cadvisor_cpu_parse_invalid_value() -> None:
    """Test cAdvisor CPU parse function handles missing or invalid values."""
    string_table = [['{"cpu_user": [{"no_value": "0.1"}], "cpu_system": [{"value": "0.15"}]}']]

    result = parse_cadvisor_cpu(string_table)

    # Should only include cpu_system (valid), not cpu_user (missing "value" key)
    assert "cpu_system" in result
    assert "cpu_user" not in result
    assert result["cpu_system"] == 0.15
