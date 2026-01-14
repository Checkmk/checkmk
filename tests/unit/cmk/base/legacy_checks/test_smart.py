#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping
from typing import Any

from cmk.base.legacy_checks.smart import (
    check_smart_temp,
    discover_smart_temp,
)
from cmk.plugins.collection.agent_based.smart import parse_raw_values


def parsed() -> Mapping[str, Any]:
    """Return parsed data from actual parse function."""
    return parse_raw_values(
        [
            [
                "/dev/sda",
                "ATA",
                "SAMSUNG_MZ7LM3T8",
                "5",
                "Reallocated_Sector_Ct",
                "0x0033",
                "100",
                "100",
                "010",
                "Pre-fail",
                "Always",
                "-",
                "0",
            ],
            [
                "/dev/sda",
                "ATA",
                "SAMSUNG_MZ7LM3T8",
                "9",
                "Power_On_Hours",
                "0x0032",
                "099",
                "099",
                "000",
                "Old_age",
                "Always",
                "-",
                "1609",
            ],
            [
                "/dev/sda",
                "ATA",
                "SAMSUNG_MZ7LM3T8",
                "194",
                "Temperature_Celsius",
                "0x0022",
                "099",
                "099",
                "000",
                "Old_age",
                "Always",
                "-",
                "30",
            ],
            [
                "/dev/nvme0n1",
                "ATA",
                "Samsung_SSD_980",
                "194",
                "Temperature_Celsius",
                "0x0022",
                "060",
                "060",
                "000",
                "Old_age",
                "Always",
                "-",
                "39",
            ],
        ]
    )


def parsed_no_temp() -> Mapping[str, Any]:
    """Return parsed data without temperature sensors."""
    return parse_raw_values(
        [
            [
                "/dev/sdb",
                "ATA",
                "SOME_DISK",
                "5",
                "Reallocated_Sector_Ct",
                "0x0033",
                "100",
                "100",
                "010",
                "Pre-fail",
                "Always",
                "-",
                "0",
            ],
            [
                "/dev/sdb",
                "ATA",
                "SOME_DISK",
                "9",
                "Power_On_Hours",
                "0x0032",
                "099",
                "099",
                "000",
                "Old_age",
                "Always",
                "-",
                "1000",
            ],
        ]
    )


def test_smart_temp_discovery() -> None:
    """Test discovery function for SMART temperature sensors."""
    section = parsed()

    discoveries = list(discover_smart_temp(section))

    # Should discover devices with temperature sensors
    assert len(discoveries) == 2

    # Extract items from discovery tuples
    items = [item for item, params in discoveries]
    assert "/dev/sda" in items
    assert "/dev/nvme0n1" in items


def test_smart_temp_discovery_no_temp() -> None:
    """Test discovery with no temperature sensors."""
    section = parsed_no_temp()

    discoveries = list(discover_smart_temp(section))

    # Should not discover anything without temperature sensors
    assert len(discoveries) == 0


def test_smart_temp_check_ok() -> None:
    """Test check function for normal temperature."""
    params = {"levels": (35, 40)}

    result = check_smart_temp("/dev/sda", params, parsed())

    # Should return a single temperature check result
    assert result is not None
    assert len(result) == 3  # state, summary, metrics
    state, summary, metrics = result
    assert state == 0  # OK state - 30°C is under 35°C threshold
    assert "30" in summary  # Temperature value
    assert "°C" in summary


def test_smart_temp_check_warning() -> None:
    """Test check function with temperature warning."""
    params = {"levels": (25, 40)}  # Lower warning threshold

    result = check_smart_temp("/dev/sda", params, parsed())

    # Should return temperature warning result
    assert result is not None
    assert len(result) == 3  # state, summary, metrics
    state, summary, metrics = result
    assert state == 1  # Warning state - 30°C > 25°C threshold
    assert "30" in summary


def test_smart_temp_check_nvme() -> None:
    """Test check function for NVMe temperature."""
    params = {"levels": (35, 40)}

    result = check_smart_temp("/dev/nvme0n1", params, parsed())

    # Should return temperature warning result
    assert result is not None
    assert len(result) == 3  # state, summary, metrics
    state, summary, metrics = result
    assert state == 1  # Warning state - 39°C > 35°C threshold
    assert "39" in summary


def test_smart_temp_check_missing_item() -> None:
    """Test check function with non-existent device."""
    params = {"levels": (35, 40)}

    results = check_smart_temp("/dev/missing", params, parsed())

    # Should return None for missing device
    assert results is None


def test_smart_temp_check_no_temperature() -> None:
    """Test check function for device without temperature sensor."""
    params = {"levels": (35, 40)}
    section = parsed_no_temp()

    results = check_smart_temp("/dev/sdb", params, section)

    # Should return None for device without temperature
    assert results is None


def test_smart_temp_parse_function() -> None:
    """Test that parse function creates expected data structure."""
    section = parsed()

    # Should have devices
    assert "/dev/sda" in section
    assert "/dev/nvme0n1" in section

    # Check /dev/sda temperature data
    sda = section["/dev/sda"]
    assert "Temperature" in sda
    assert sda["Temperature"] == 30
    assert "Power_On_Hours" in sda
    assert sda["Power_On_Hours"] == 1609

    # Check /dev/nvme0n1 temperature data
    nvme = section["/dev/nvme0n1"]
    assert "Temperature" in nvme
    assert nvme["Temperature"] == 39
