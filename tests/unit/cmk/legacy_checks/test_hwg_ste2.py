#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

import pytest

from cmk.agent_based.internal import evaluate_snmp_detection
from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.legacy_checks import hwg_temp
from cmk.legacy_checks.hwg_temp import (
    check_hwg_temp,
    discover_hwg_temp,
    snmp_section_hwg_ste2,
)
from cmk.plugins.hwg.agent_based.hwg_humidity import (
    check_hwg_humidity,
    discover_hwg_humidity,
)
from cmk.plugins.hwg.agent_based.lib import parse_hwg
from cmk.plugins.lib.temperature import TempParamDict


@pytest.fixture(autouse=True)
def _patch_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hwg_temp, "get_value_store", lambda: {})


def test_detect_hwg_ste2() -> None:
    assert (detect_spec := snmp_section_hwg_ste2.detect)
    assert evaluate_snmp_detection(
        detect_spec=detect_spec,
        oid_value_getter={".1.3.6.1.2.1.1.1.0": "contains STE2"}.get,
    )


def test_hwg_ste2_parse() -> None:
    """Test parsing of SNMP data for hwg_ste2."""
    string_table = [
        ["1", "Sensor 215", "1", "23.8", "1"],  # index, descr, status, value, unit (1=C)
        ["2", "Sensor 216", "1", "34.6", "4"],  # index, descr, status, value, unit (4=%)
    ]

    result = parse_hwg(string_table)

    expected = {
        "1": {
            "descr": "Sensor 215",
            "dev_unit": "c",
            "temperature": 23.8,
            "dev_status_name": "normal",
            "dev_status": "1",
        },
        "2": {
            "descr": "Sensor 216",
            "humidity": 34.6,
            "dev_status_name": "normal",
            "dev_status": "1",
        },
    }

    assert result == expected


def test_hwg_ste2_temperature_discovery() -> None:
    """Test discovery of temperature sensors."""
    parsed = {
        "1": {
            "descr": "Sensor 215",
            "dev_unit": "c",
            "temperature": 23.8,
            "dev_status_name": "normal",
            "dev_status": "1",
        },
        "2": {
            "descr": "Sensor 216",
            "humidity": 34.6,
            "dev_status_name": "normal",
            "dev_status": "1",
        },
    }

    discovery_result = list(discover_hwg_temp(parsed))

    expected = [Service(item="1")]

    assert discovery_result == expected


def test_hwg_ste2_humidity_discovery() -> None:
    """Test discovery of humidity sensors."""
    parsed = {
        "1": {
            "descr": "Sensor 215",
            "dev_unit": "c",
            "temperature": 23.8,
            "dev_status_name": "normal",
            "dev_status": "1",
        },
        "2": {
            "descr": "Sensor 216",
            "humidity": 34.6,
            "dev_status_name": "normal",
            "dev_status": "1",
        },
    }

    discovery_result = list(discover_hwg_humidity(parsed))

    assert discovery_result == [Service(item="2")]


def test_hwg_ste2_temperature_check() -> None:
    """Test temperature check function."""
    parsed = {
        "1": {
            "descr": "Sensor 215",
            "dev_unit": "c",
            "temperature": 23.8,
            "dev_status_name": "normal",
            "dev_status": "1",
        },
    }
    params: TempParamDict = {"levels": (30.0, 35.0)}

    results = list(check_hwg_temp("1", params, parsed))

    # Should contain Metric, Result (reading), and Result (description)
    result_objs = [r for r in results if isinstance(r, Result)]
    metric_objs = [r for r in results if isinstance(r, Metric)]

    assert len(result_objs) >= 2
    assert len(metric_objs) >= 1

    # Check reading result
    reading_result = result_objs[0]
    assert reading_result.state == State.OK
    assert "23.8" in reading_result.summary
    assert "\u00b0C" in reading_result.summary

    # Check description result
    desc_result = result_objs[-1]
    assert "Description: Sensor 215" in desc_result.summary
    assert "Status: normal" in desc_result.summary

    # Check metric
    assert metric_objs[0].name == "temp"


def test_hwg_ste2_humidity_check() -> None:
    """Test humidity check function."""
    parsed = {
        "2": {
            "descr": "Sensor 216",
            "humidity": 34.6,
            "dev_status_name": "normal",
            "dev_status": "1",
        },
    }
    params = {"levels": (60.0, 70.0)}

    results = list(check_hwg_humidity("2", params, parsed))
    assert len(results) == 3

    assert isinstance(results[0], Result)
    assert results[0].state == State.OK
    assert "34.60%" in results[0].summary

    assert isinstance(results[1], Metric)
    assert results[1].name == "humidity"

    assert isinstance(results[2], Result)
    assert results[2].state == State.OK
    assert "Description: Sensor 216" in results[2].summary
    assert "Status: normal" in results[2].summary


def test_hwg_ste2_temperature_missing_item() -> None:
    """Test temperature check with missing item."""
    parsed = {"1": {"temperature": 23.8}}
    params: TempParamDict = {"levels": (30.0, 35.0)}

    result = list(check_hwg_temp("999", params, parsed))

    assert not result


def test_hwg_ste2_humidity_missing_item() -> None:
    """Test humidity check with missing item."""
    parsed = {"2": {"humidity": 34.6}}
    params = {"levels": (60, 70)}

    result = list(check_hwg_humidity("999", params, parsed))

    assert result == []
