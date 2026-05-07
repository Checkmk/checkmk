#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from cmk.agent_based.v2 import Result, Service
from cmk.plugins.allnet.agent_based.allnet_ip_sensoric import (
    check_allnet_ip_sensoric_humidity,
    check_allnet_ip_sensoric_pressure,
    check_allnet_ip_sensoric_tension,
    discover_allnet_ip_sensoric_humidity,
    discover_allnet_ip_sensoric_pressure,
    discover_allnet_ip_sensoric_temp,
    discover_allnet_ip_sensoric_tension,
)
from cmk.plugins.allnet_ip_sensoric.agent_based.allnet_ip_sensoric import parse_allnet_ip_sensoric

_SECTION = parse_allnet_ip_sensoric(
    [
        ["sensor1.max_abs_float", "38.18"],
        ["sensor1.max_day_float", "25.31"],
        ["sensor1.min_abs_float", "20.12"],
        ["sensor1.min_day_float", "25.06"],
        ["sensor1.name", "Gerät Intern"],
        ["sensor1.unit", "°C"],
        ["sensor1.value_display", "25.18 °C"],
        ["sensor1.value_float", "25.18"],
        ["sensor1.value_int", "2518"],
        ["sensor1.value_string", "25.18"],
        ["sensor2.alarm1", "0"],
        ["sensor2.function", "2"],
        ["sensor2.limit_high", "25.00"],
        ["sensor2.limit_low", "5.00"],
        ["sensor2.maximum", "0.00"],
        ["sensor2.minimum", "100.00"],
        ["sensor2.name", "Humidity1"],
        ["sensor2.value_float", "10.00"],
        ["sensor2.value_int", "10"],
        ["sensor2.value_string", "10.00"],
        ["sensor105.max_abs_float", "70.06"],
        ["sensor105.max_day_float", "61.47"],
        ["sensor105.min_abs_float", "51.29"],
        ["sensor105.min_day_float", "59.93"],
        ["sensor105.name", "Feuchtigkeit"],
        ["sensor105.unit", "%"],
        ["sensor105.value_display", "60.62 %"],
        ["sensor105.value_float", "60.62"],
        ["sensor105.value_int", "6061"],
        ["sensor105.value_string", "60.62"],
        ["sensor112.max_abs_float", "20.71"],
        ["sensor112.max_day_float", "20.26"],
        ["sensor112.min_abs_float", "19.58"],
        ["sensor112.min_day_float", "19.56"],
        ["sensor112.name", "Serverraum"],
        ["sensor112.unit", "°C"],
        ["sensor112.value_display", "19.80 °C"],
        ["sensor112.value_float", "19.80"],
        ["sensor112.value_int", "1979"],
        ["sensor112.value_string", "19.80"],
        ["sensor113.max_abs_float", "49.54"],
        ["sensor113.max_day_float", "46.53"],
        ["sensor113.min_abs_float", "44.30"],
        ["sensor113.min_day_float", "44.30"],
        ["sensor113.name", "Serverraum"],
        ["sensor113.unit", "%"],
        ["sensor113.value_display", "45.70 %"],
        ["sensor113.value_float", "45.70"],
        ["sensor113.value_int", "4570"],
        ["sensor113.value_string", "45.70"],
        ["sensor115.max_abs_float", "23.43"],
        ["sensor115.max_day_float", "21.56"],
        ["sensor115.min_abs_float", "20.75"],
        ["sensor115.min_day_float", "21.18"],
        ["sensor115.name", "Schrank 8"],
        ["sensor115.unit", "°C"],
        ["sensor115.value_display", "21.50 °C"],
        ["sensor115.value_float", "21.50"],
        ["sensor115.value_int", "2150"],
        ["sensor115.value_string", "21.50"],
        ["sensor130.max_abs_float", "18.93"],
        ["sensor130.max_day_float", "17.00"],
        ["sensor130.min_abs_float", "16.37"],
        ["sensor130.min_day_float", "16.37"],
        ["sensor130.name", "Dachboden"],
        ["sensor130.unit", "°C"],
        ["sensor130.value_display", "16.56 °C"],
        ["sensor130.value_float", "16.56"],
        ["sensor130.value_int", "1655"],
        ["sensor130.value_string", "16.56"],
        ["system.date", "29.10.2014"],
        ["system.devicename", "ALL4500"],
        ["system.devicetype", "ALL4500"],
        ["system.sys", "66141"],
        ["system.time", "08:28:36"],
    ]
)


def test_discover_humidity() -> None:
    assert sorted(discover_allnet_ip_sensoric_humidity(_SECTION), key=lambda s: s.item or "") == [
        Service(item="Feuchtigkeit Sensor 105"),
        Service(item="Humidity1 Sensor 2"),
        Service(item="Serverraum Sensor 113"),
    ]


def test_discover_temp() -> None:
    assert sorted(discover_allnet_ip_sensoric_temp(_SECTION), key=lambda s: s.item or "") == [
        Service(item="Dachboden Sensor 130"),
        Service(item="Gerät Intern Sensor 1"),
        Service(item="Schrank 8 Sensor 115"),
        Service(item="Serverraum Sensor 112"),
    ]


def test_discover_tension() -> None:
    assert list(discover_allnet_ip_sensoric_tension(_SECTION)) == []


def test_discover_pressure() -> None:
    assert list(discover_allnet_ip_sensoric_pressure(_SECTION)) == []


def test_check_humidity() -> None:
    params = {"levels": (60.0, 65.0), "levels_lower": (40.0, 35.0)}
    results = list(check_allnet_ip_sensoric_humidity("Humidity1 Sensor 2", params, _SECTION))
    assert any(isinstance(r, Result) for r in results)


def test_check_pressure_not_found() -> None:
    assert list(check_allnet_ip_sensoric_pressure("nonexistent Sensor 99", _SECTION)) == []


def test_check_tension_not_found() -> None:
    assert list(check_allnet_ip_sensoric_tension("nonexistent Sensor 99", _SECTION)) == []
