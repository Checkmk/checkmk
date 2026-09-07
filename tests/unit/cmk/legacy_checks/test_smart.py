#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.


import pytest

from cmk.legacy_checks.smart import _check_smart_temp, discover_smart_temp
from cmk.plugins.lib.temperature import TempParamType
from cmk.plugins.smart.agent_based.smart import parse_raw_values, Section

DELTA_KEY = "temp.smart_/dev/sda.delta"
TREND_KEY = "temp.smart_/dev/sda.trend"
LAST_CHECK = 1767225600.0
CHECK_INTERVAL = 600.0


def parsed() -> Section:
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


def parsed_no_temp() -> Section:
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
    params: TempParamType = {"levels": (35.0, 40.0)}

    result = _check_smart_temp("/dev/sda", params, parsed(), {}, LAST_CHECK)

    # Should return a single temperature check result
    assert result is not None
    assert len(result) == 3  # state, summary, metrics
    state, summary, metrics = result
    assert state == 0  # OK state - 30°C is under 35°C threshold
    assert "30" in summary  # Temperature value
    assert "°C" in summary


def test_smart_temp_check_warning() -> None:
    """Test check function with temperature warning."""
    params: TempParamType = {"levels": (25.0, 40.0)}  # Lower warning threshold

    result = _check_smart_temp("/dev/sda", params, parsed(), {}, LAST_CHECK)

    # Should return temperature warning result
    assert result is not None
    assert len(result) == 3  # state, summary, metrics
    state, summary, metrics = result
    assert state == 1  # Warning state - 30°C > 25°C threshold
    assert "30" in summary


def test_smart_temp_check_nvme() -> None:
    """Test check function for NVMe temperature."""
    params: TempParamType = {"levels": (35.0, 40.0)}

    result = _check_smart_temp("/dev/nvme0n1", params, parsed(), {}, LAST_CHECK)

    # Should return temperature warning result
    assert result is not None
    assert len(result) == 3  # state, summary, metrics
    state, summary, metrics = result
    assert state == 1  # Warning state - 39°C > 35°C threshold
    assert "39" in summary


def test_smart_temp_check_missing_item() -> None:
    """Test check function with non-existent device."""
    params: TempParamType = {"levels": (35.0, 40.0)}

    results = _check_smart_temp("/dev/missing", params, parsed(), {}, LAST_CHECK)

    # Should return None for missing device
    assert results is None


def test_smart_temp_check_no_temperature() -> None:
    """Test check function for device without temperature sensor."""
    params: TempParamType = {"levels": (35.0, 40.0)}
    section = parsed_no_temp()

    results = _check_smart_temp("/dev/sdb", params, section, {}, LAST_CHECK)

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


def parsed_unmapped_temp_attribute() -> Section:
    return parse_raw_values(
        [
            [
                "/dev/sdc",
                "ATA",
                "SOME_SSD",
                "231",
                "Temperature_Celsius",
                "0x0013",
                "100",
                "100",
                "010",
                "Pre-fail",
                "Always",
                "-",
                "33",
            ],
        ]
    )


def test_smart_temp_discovered_but_not_checkable() -> None:
    section = parsed_unmapped_temp_attribute()

    assert list(discover_smart_temp(section)) == [("/dev/sdc", {})]
    assert _check_smart_temp("/dev/sdc", {"levels": (35.0, 40.0)}, section, {}, LAST_CHECK) is None


@pytest.mark.parametrize(
    "params, expected",
    [
        pytest.param(
            {"levels": (25.0, 40.0), "device_levels_handling": "usr"},
            (1, "30 °C (warn/crit at 25.0/40.0 °C)", [("temp", 30, 25.0, 40.0)]),
            id="usr",
        ),
        pytest.param(
            {"levels": (25.0, 40.0), "device_levels_handling": "dev"},
            (0, "30 °C", [("temp", 30, None, None)]),
            id="dev_has_no_levels_to_offer",
        ),
        pytest.param(
            {"levels": (25.0, 40.0), "device_levels_handling": "best"},
            (1, "30 °C (warn/crit at 25.0/40.0 °C)", [("temp", 30, 25.0, 40.0)]),
            id="best",
        ),
        pytest.param(
            {"levels": (25.0, 40.0), "device_levels_handling": "worst"},
            (1, "30 °C (warn/crit at 25.0/40.0 °C)", [("temp", 30, 25.0, 40.0)]),
            id="worst",
        ),
        pytest.param(
            {"levels": (25.0, 40.0), "device_levels_handling": "devdefault"},
            (1, "30 °C (warn/crit at 25.0/40.0 °C)", [("temp", 30, 25.0, 40.0)]),
            id="devdefault_falls_back_to_the_user_levels",
        ),
        pytest.param(
            {"levels_lower": (35.0, 32.0)},
            (2, "30 °C (warn/crit below 35.0/32.0 °C)", [("temp", 30, None, None)]),
            id="lower_levels_only",
        ),
        pytest.param(
            {"levels": (None, None)},
            (0, "30 °C", [("temp", 30, None, None)]),
            id="levels_collapsing_to_none",
        ),
    ],
)
def test_smart_temp_check_levels(params: TempParamType, expected: object) -> None:
    assert _check_smart_temp("/dev/sda", params, parsed(), {}, LAST_CHECK) == expected


@pytest.mark.parametrize(
    "previous_reading, params, expected",
    [
        pytest.param(
            20.0,
            {"levels": (35.0, 40.0), "trend_compute": {"period": 5, "trend_levels": (1.0, 2.0)}},
            (
                2,
                "30 °C, rate: +5.0/5 min, rising faster than 2.0/5 min(!!)",
                [("temp", 30, 35.0, 40.0)],
            ),
            id="rising_crit",
        ),
        pytest.param(
            20.0,
            {"levels": (35.0, 40.0), "trend_compute": {"period": 5, "trend_levels": (2.0, 10.0)}},
            (
                1,
                "30 °C, rate: +5.0/5 min, rising faster than 2.0/5 min(!)",
                [("temp", 30, 35.0, 40.0)],
            ),
            id="rising_warn",
        ),
        pytest.param(
            20.0,
            {"levels": (35.0, 40.0), "trend_compute": {"period": 5}},
            (0, "30 °C, rate: +5.0/5 min", [("temp", 30, 35.0, 40.0)]),
            id="rate_without_trend_levels_never_alerts",
        ),
        pytest.param(
            40.0,
            {
                "levels": (35.0, 40.0),
                "trend_compute": {"period": 5, "trend_levels_lower": (1.0, 2.0)},
            },
            (
                2,
                "30 °C, rate: -5.0/5 min, falling faster than -2.0/5 min(!!)",
                [("temp", 30, 35.0, 40.0)],
            ),
            id="falling_crit",
        ),
        pytest.param(
            40.0,
            {
                "levels": (35.0, 40.0),
                "trend_compute": {"period": 5, "trend_levels_lower": (2.0, 10.0)},
            },
            (
                1,
                "30 °C, rate: -5.0/5 min, falling faster than -2.0/5 min(!)",
                [("temp", 30, 35.0, 40.0)],
            ),
            id="falling_warn",
        ),
        pytest.param(
            29.0,
            {"levels": (35.0, 40.0), "trend_compute": {"period": 5, "trend_timeleft": (200, 50)}},
            (
                1,
                "30 °C, rate: +0.5/5 min, 1h 40m until temp limit reached(!)",
                [("temp", 30, 35.0, 40.0)],
            ),
            id="timeleft_warn_renders_hours",
        ),
        pytest.param(
            40.0,
            {
                "levels_lower": (20.0, 10.0),
                "trend_compute": {"period": 5, "trend_timeleft": (100, 50)},
            },
            (
                2,
                "30 °C, rate: -5.0/5 min, 20 minutes until temp limit reached(!!)",
                [("temp", 30, None, None)],
            ),
            id="timeleft_of_a_falling_temperature_counts_down_to_the_lower_crit",
        ),
        pytest.param(
            20.0,
            {"trend_compute": {"period": 5, "trend_timeleft": (100, 50)}},
            (0, "30 °C, rate: +5.0/5 min", [("temp", 30, None, None)]),
            id="timeleft_without_a_crit_level_has_no_limit_to_count_down_to",
        ),
        pytest.param(
            30.0,
            {"levels": (35.0, 40.0), "trend_compute": {"period": 5, "trend_timeleft": (100, 50)}},
            (0, "30 °C, rate: 0.0/5 min", [("temp", 30, 35.0, 40.0)]),
            id="timeleft_of_a_flat_temperature_is_infinite",
        ),
    ],
)
def test_smart_temp_check_trend(
    previous_reading: float,
    params: TempParamType,
    expected: object,
) -> None:
    value_store: dict[str, object] = {
        DELTA_KEY: (LAST_CHECK, previous_reading),
        TREND_KEY: (LAST_CHECK, 0.0),
    }
    assert (
        _check_smart_temp("/dev/sda", params, parsed(), value_store, LAST_CHECK + CHECK_INTERVAL)
        == expected
    )
    assert set(value_store) == {DELTA_KEY, TREND_KEY}


def test_smart_temp_check_trend_on_the_first_execution() -> None:
    params: TempParamType = {"levels": (35.0, 40.0), "trend_compute": {"period": 5}}
    value_store: dict[str, object] = {}

    expected: object = (
        3,
        (
            "30 °C, Counter 'temp.smart_/dev/sda.delta' has been initialized. "
            "Result available on second check execution."
        ),
        [("temp", 30, 35.0, 40.0)],
    )

    assert _check_smart_temp("/dev/sda", params, parsed(), value_store, LAST_CHECK) == expected
    assert set(value_store) == {DELTA_KEY}
