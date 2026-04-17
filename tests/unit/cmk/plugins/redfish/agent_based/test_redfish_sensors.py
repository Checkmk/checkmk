#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Callable
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, StringTable
from cmk.plugins.redfish.agent_based.redfish_sensors import (
    _check_sensor_levels,
    discovery_redfish_sensors,
)
from cmk.plugins.redfish.lib import (
    _threshold_value,
    detect_vendor,
    parse_redfish_multiple,
    Perfdata,
    process_redfish_perfdata,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_modern_sensor(
    sensor_id: str = "BMC_TEMP",
    *,
    reading: float = 31.875,
    reading_type: str = "Temperature",
    reading_units: str = "Cel",
    upper_caution: float | None = 105.0,
    upper_critical: float | None = 108.0,
    lower_caution: float | None = 5.0,
    lower_critical: float | None = None,
    health: str = "OK",
    state: str = "Enabled",
) -> dict[str, Any]:
    thresholds: dict[str, Any] = {}
    if upper_caution is not None:
        thresholds["UpperCaution"] = {"Reading": upper_caution}
    if upper_critical is not None:
        thresholds["UpperCritical"] = {"Reading": upper_critical}
    if lower_caution is not None:
        thresholds["LowerCaution"] = {"Reading": lower_caution}
    if lower_critical is not None:
        thresholds["LowerCritical"] = {"Reading": lower_critical}
    return {
        "@odata.id": f"/redfish/v1/Chassis/MGX_BMC_0/Sensors/{sensor_id}",
        "@odata.type": "#Sensor.v1_7_0.Sensor",
        "Id": sensor_id,
        "Name": sensor_id.replace("_", " "),
        "Reading": reading,
        "ReadingType": reading_type,
        "ReadingUnits": reading_units,
        "Status": {"Health": health, "State": state},
        **({"Thresholds": thresholds} if thresholds else {}),
    }


def _make_legacy_sensor(
    sensor_id: str = "CPU1_Temp",
    *,
    reading_celsius: float = 42.0,
    upper_warn: float | None = 80.0,
    upper_crit: float | None = 90.0,
    lower_warn: float | None = 5.0,
    lower_crit: float | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "ReadingCelsius": reading_celsius,
    }
    if upper_warn is not None:
        entry["UpperThresholdNonCritical"] = upper_warn
    if upper_crit is not None:
        entry["UpperThresholdCritical"] = upper_crit
    if lower_warn is not None:
        entry["LowerThresholdNonCritical"] = lower_warn
    if lower_crit is not None:
        entry["LowerThresholdCritical"] = lower_crit
    return entry


def _make_string_table(*entries: dict[str, Any]) -> StringTable:
    return [[json.dumps(e)] for e in entries]


# ---------------------------------------------------------------------------
# process_redfish_perfdata — threshold extraction
# ---------------------------------------------------------------------------


class TestProcessRedfishPerfdata:
    def test_modern_nested_thresholds(self) -> None:
        entry = _make_modern_sensor(
            reading=31.875, upper_caution=105.0, upper_critical=108.0, lower_caution=5.0
        )
        result = process_redfish_perfdata(entry)
        assert result is not None
        assert result.value == 31.875
        assert result.levels_upper == ("fixed", (105.0, 108.0))
        assert result.levels_lower == ("fixed", (5.0, float("-inf")))

    def test_legacy_flat_thresholds(self) -> None:
        entry = _make_legacy_sensor(
            reading_celsius=42.0, upper_warn=80.0, upper_crit=90.0, lower_warn=5.0
        )
        result = process_redfish_perfdata(entry)
        assert result is not None
        assert result.value == 42.0
        assert result.levels_upper == ("fixed", (80.0, 90.0))
        assert result.levels_lower == ("fixed", (5.0, float("-inf")))

    def test_flat_takes_priority_over_nested(self) -> None:
        entry: dict[str, Any] = {
            "Reading": 50.0,
            "UpperThresholdNonCritical": 80.0,
            "UpperThresholdCritical": 90.0,
            "Thresholds": {
                "UpperCaution": {"Reading": 999.0},
                "UpperCritical": {"Reading": 999.0},
            },
        }
        result = process_redfish_perfdata(entry)
        assert result is not None
        assert result.levels_upper == ("fixed", (80.0, 90.0))

    def test_flat_zero_threshold_does_not_fall_through(self) -> None:
        """Verify _threshold_value returns the flat 0.0, not the nested -5.0."""
        entry: dict[str, Any] = {"LowerThresholdCritical": 0.0}
        thresholds: dict[str, Any] = {"LowerCritical": {"Reading": -5.0}}
        result = _threshold_value(entry, "LowerThresholdCritical", thresholds, "LowerCritical")
        assert result == 0.0

    def test_no_thresholds_at_all(self) -> None:
        entry: dict[str, Any] = {"Reading": 25.0}
        result = process_redfish_perfdata(entry)
        assert result is not None
        assert result.value == 25.0
        assert result.levels_upper is None
        assert result.levels_lower is None

    def test_no_reading_returns_none(self) -> None:
        entry: dict[str, Any] = {"Name": "SomeSensor"}
        assert process_redfish_perfdata(entry) is None


# ---------------------------------------------------------------------------
# detect_vendor
# ---------------------------------------------------------------------------


class TestDetectVendor:
    def test_nvidia_from_vendor_field(self) -> None:
        root_data: dict[str, Any] = {"Oem": {}, "Vendor": "NVIDIA"}
        vendor = detect_vendor(root_data)
        assert vendor.name == "NVIDIA"
        assert vendor.expand_string == "?$expand=*($levels=1)"

    def test_existing_vendors_unchanged(self) -> None:
        root_data: dict[str, Any] = {"Oem": {"Dell": {}}}
        vendor = detect_vendor(root_data)
        assert vendor.name == "Dell"

    def test_generic_fallback(self) -> None:
        root_data: dict[str, Any] = {"Oem": {}, "Vendor": "SomeNewVendor"}
        vendor = detect_vendor(root_data)
        assert vendor.name == "Generic"


# ---------------------------------------------------------------------------
# discovery + check — redfish_sensors
# ---------------------------------------------------------------------------


class TestRedfishSensorsDiscovery:
    def test_discovers_enabled_sensor(self) -> None:
        sensor = _make_modern_sensor("BMC_TEMP")
        parsed = parse_redfish_multiple(_make_string_table(sensor))
        services = list(discovery_redfish_sensors(parsed))
        assert len(services) == 1
        assert services[0].item == "BMC_TEMP"

    def test_skips_absent_sensor(self) -> None:
        sensor = _make_modern_sensor("ABSENT_TEMP", state="Absent")
        parsed = parse_redfish_multiple(_make_string_table(sensor))
        services = list(discovery_redfish_sensors(parsed))
        assert len(services) == 0

    def test_discovers_multiple_sensors(self) -> None:
        sensors = [
            _make_modern_sensor("BMC_TEMP"),
            _make_modern_sensor("CPU_TEMP", reading=55.0),
        ]
        parsed = parse_redfish_multiple(_make_string_table(*sensors))
        items = {s.item for s in discovery_redfish_sensors(parsed)}
        assert items == {"BMC_TEMP", "CPU_TEMP"}


class TestThresholdValue:
    def test_flat_present(self) -> None:
        entry: dict[str, Any] = {"UpperThresholdCritical": 90.0}
        assert _threshold_value(entry, "UpperThresholdCritical", {}, "UpperCritical") == 90.0

    def test_nested_fallback(self) -> None:
        thresholds: dict[str, Any] = {"UpperCritical": {"Reading": 108.0}}
        assert _threshold_value({}, "UpperThresholdCritical", thresholds, "UpperCritical") == 108.0

    def test_flat_preferred_over_nested(self) -> None:
        entry: dict[str, Any] = {"UpperThresholdCritical": 90.0}
        thresholds: dict[str, Any] = {"UpperCritical": {"Reading": 999.0}}
        assert (
            _threshold_value(entry, "UpperThresholdCritical", thresholds, "UpperCritical") == 90.0
        )

    def test_neither_present(self) -> None:
        assert _threshold_value({}, "UpperThresholdCritical", {}, "UpperCritical") is None


# ---------------------------------------------------------------------------
# _check_sensor_levels — new ReadingType metrics
# ---------------------------------------------------------------------------


class TestCheckSensorLevels:
    @pytest.mark.parametrize(
        "metric_name, label, render_func, value, expected_summary_contains",
        [
            ("fan", "Speed", lambda v: f"{v:.0f} rpm", 3720.0, "3720 rpm"),
            ("voltage", "Voltage", lambda v: f"{v:.1f} V", 12.1, "12.1 V"),
            ("current", "Current", lambda v: f"{v:.1f} A", 2.5, "2.5 A"),
            ("power", "Power", lambda v: f"{v:.1f} W", 174.0, "174.0 W"),
            ("frequency", "Frequency", lambda v: f"{v:.1f} Hz", 50.0, "50.0 Hz"),
        ],
    )
    def test_produces_metric_and_result(
        self,
        metric_name: str,
        label: str,
        render_func: Callable[[float], str],
        value: float,
        expected_summary_contains: str,
    ) -> None:
        perfdata = Perfdata(
            value=value,
            levels_upper=None,
            levels_lower=None,
            boundaries=(None, None),
        )
        results = list(
            _check_sensor_levels(
                perfdata, metric_name=metric_name, label=label, render_func=render_func
            )
        )
        result_items = [r for r in results if isinstance(r, Result)]
        metric_items = [r for r in results if isinstance(r, Metric)]
        assert len(result_items) >= 1
        assert len(metric_items) >= 1
        assert metric_items[0].name == metric_name
        assert metric_items[0].value == value
        assert expected_summary_contains in result_items[0].summary
