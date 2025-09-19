#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from typing import Any

from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.base.legacy_checks.apc_rackpdu_power import discover_apc_rackpdu_power
from cmk.plugins.collection.agent_based.apc_rackpdu_power import parse_apc_rackpdu_power


def test_apc_rackpdu_power_1() -> None:
    """Test apc_rackpdu_power check."""

    # Test data from generictests/datasets/apc_rackpdu_power_1.py
    raw_data = [
        [["luz0010x", "0"]],
        [["3"]],
        [["0", "1", "1", "0"], ["0", "1", "2", "0"], ["0", "1", "3", "0"]],
    ]

    # Parse the data using the modern agent-based parser
    parsed_section = parse_apc_rackpdu_power(raw_data)
    assert parsed_section is not None

    # Test discovery
    discovery_result = list(discover_apc_rackpdu_power(parsed_section))

    expected_discovery: list[tuple[str, dict[str, Any]]] = [
        ("Device luz0010x", {}),
        ("Phase 1", {}),
        ("Phase 2", {}),
        ("Phase 3", {}),
    ]

    assert sorted(discovery_result) == sorted(expected_discovery)

    # Test check function for device
    params: dict[str, Any] = {}
    device_result = list(check_elphase("Device luz0010x", params, parsed_section))

    # Expected: Device should show power measurement
    assert len(device_result) == 1
    result = device_result[0]
    assert result[0] == 0  # OK state
    assert "Power: 0.0 W" in result[1]
    assert result[2][0][0] == "power"  # Metric name
    assert result[2][0][1] == 0.0  # Metric value

    # Test check function for phase
    phase_result = list(check_elphase("Phase 1", params, parsed_section))

    # Expected: Phase should show current measurement and status
    assert len(phase_result) == 2
    current_result, status_result = phase_result

    assert current_result[0] == 0  # OK state
    assert "Current: 0.0 A" in current_result[1]
    assert current_result[2][0][0] == "current"  # Metric name
    assert current_result[2][0][1] == 0.0  # Metric value

    assert status_result[0] == 0  # OK state
    assert "load normal" in status_result[1]
