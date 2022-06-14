#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName, SectionName

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.plugins.agent_based.cmciii as cmciii
import cmk.base.plugins.agent_based.cmciii_phase as cmciii_phase
import cmk.base.plugins.agent_based.cmciii_status as cmciii_status
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State


@pytest.mark.parametrize(
    "variable, expected",
    [
        ("", ["", "", ""]),
        ("one", ["", "", "one"]),
        ("one.two", ["one", "", "two"]),
        ("one.two.three", ["one", "two", "three"]),
    ],
)
def test_sanitize_variable(variable, expected) -> None:
    assert cmciii.sanitize_variable(variable) == expected


@pytest.mark.parametrize(
    "table, var_type, variable, expected",
    [
        ("not_phase", "", ["var_end"], "var_end"),
        ("phase", "2", ["Phase", "TWO", "THREE", "FOUR", "END"], "two_three_four"),
        ("phase", "2", ["ONE", "Phase", "THREE", "FOUR", "END"], "three_four"),
        ("phase", "2", ["ONE", "TWO", "THREE", "FOUR", "END"], "three_four"),
        ("phase", "not 2", ["Phase", "TWO", "THREE", "FOUR", "END"], "TWO THREE FOUR"),
        ("phase", "not 2", ["ONE", "Phase", "THREE", "FOUR", "END"], "THREE FOUR"),
        ("phase", "not 2", ["ONE", "TWO", "THREE", "FOUR", "END"], "THREE FOUR"),
    ],
)
def test_sensor_key(table, var_type, variable, expected) -> None:
    assert cmciii.sensor_key(table, var_type, variable) == expected


@pytest.mark.parametrize(
    "sensor_type, variable, expected",
    [
        ("temp", ["FooTemperature", "Var"], "Foo device"),
        ("temp", ["Temperature", "In-Var"], "Ambient device In"),
        ("temp", ["Temperature", "Out-Var"], "Ambient device Out"),
        ("phase", ["Phase L 1"], "device Phase 1"),
        ("phase", ["Phase L 1", "three"], "device Phase 1"),
        ("phase", ["one", "Phase1"], "device one Phase 1"),
        ("phase", ["one", "Phase1", "three"], "device one Phase 1"),
        ("psm_plugs", ["one", "two"], "device one.two"),
        ("can_current", ["one", "two"], "device one.two"),
        ("other_sensors", ["one"], "device one"),
        ("other_sensors", ["one", "two"], "device one"),
    ],
)
def test_sensor_id(sensor_type, variable, expected) -> None:
    assert cmciii.sensor_id(sensor_type, variable, "device") == expected


def test_sensor_id_temp_in_out() -> None:
    assert cmciii.sensor_id("temp_in_out", ["Air"], "Liquid_Cooling_Package") == "Air LCP"


def run_discovery(section, plugin, info, params=None):
    section_plugin = agent_based_register.get_section_plugin(SectionName(section))
    assert section_plugin
    plugin = agent_based_register.get_check_plugin(CheckPluginName(plugin))
    assert plugin
    section = section_plugin.parse_function(info)
    if params is None:
        return sorted(plugin.discovery_function(section=section))
    return sorted(plugin.discovery_function(params=params, section=section))


def run_check(section, plugin, item, info, params=None):
    section_plugin = agent_based_register.get_section_plugin(SectionName(section))
    assert section_plugin
    plugin = agent_based_register.get_check_plugin(CheckPluginName(plugin))
    assert plugin
    if params is None:
        return list(plugin.check_function(item=item, section=section_plugin.parse_function(info)))
    return list(
        plugin.check_function(item=item, params=params, section=section_plugin.parse_function(info))
    )


def _leakage_info(status, position):
    return [
        [["4", "CMCIII-LEAK", "CMCIII-LEAK", "2"]],
        [
            ["4.1", "Leakage.DescName", "1", "", "0", "Leakage", "0"],
            ["4.2", "Leakage.Position", "33", "", "0", position, "0"],
            ["4.3", "Leakage.Delay", "21", "s", "1", "1 s", "1"],
            ["4.4", "Leakage.Status", "7", "", "0", status, "4"],
            ["4.5", "Leakage.Category", "14", "", "0", "0", "0"],
        ],
    ]


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize(
    "status, position, expected",
    [
        (
            "OK",
            "None",
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(state=State.OK, summary="Delay: 1 s"),
            ],
        ),
        (
            "ProbeOpen",
            "None",
            [
                Result(state=State.CRIT, summary="Status: ProbeOpen"),
                Result(state=State.OK, summary="Delay: 1 s"),
            ],
        ),
        (
            "Alarm",
            "Zone 1",
            [
                Result(state=State.CRIT, summary="Status: Alarm"),
                Result(state=State.OK, summary="Delay: 1 s"),
            ],
        ),
    ],
)
def test_cmciii_leakage_sensors(status, position, expected) -> None:
    assert (
        run_check(
            "cmciii",
            "cmciii_leakage",
            "CMCIII-LEAK Leakage",
            _leakage_info(status, position),
            params={},
        )
        == expected
    )


def _lcp_sensor():
    return [
        [["2", "LCP-I Flush 30kW", "Liquid Cooling Package", "2"]],
        [
            ["2.1", "Air.Device.DescName", "1", "", "0", "Fan Unit", "0"],
            ["2.2", "Air.Device.Software Revision", "91", "", "0", "V09.005", "0"],
            ["2.3", "Air.Device.Hardware Revision", "91", "", "0", "V0000", "0"],
            ["2.4", "Air.Device.Status", "7", "", "0", "OK", "4"],
            ["2.5", "Air.Device.Category", "14", "", "0", "2", "2"],
            ["2.6", "Air.Temperature.DescName", "1", "", "0", "Air-Temperatures", "0"],
            ["2.7", "Air.Temperature.In-Top", "2", "°C", "-10", "19.8 °C", "198"],
            ["2.8", "Air.Temperature.In-Mid", "2", "°C", "-10", "19.0 °C", "190"],
            ["2.9", "Air.Temperature.In-Bot", "2", "°C", "-10", "18.2 °C", "182"],
            ["2.10", "Air.Temperature.Out-Top", "2", "°C", "-10", "19.9 °C", "199"],
            ["2.11", "Air.Temperature.Out-Mid", "2", "°C", "-10", "18.9 °C", "189"],
            ["2.12", "Air.Temperature.Out-Bot", "2", "°C", "-10", "18.0 °C", "180"],
            ["2.13", "Air.Temperature.Status", "7", "", "0", "OK", "4"],
            ["2.14", "Air.Temperature.Category", "14", "", "0", "2", "2"],
            ["2.15", "Air.Server-In.DescName", "1", "", "0", "Server-In", "0"],
            ["2.16", "Air.Server-In.Setpoint", "17", "°C", "-10", "23.0 °C", "230"],
            ["2.17", "Air.Server-In.Average", "2", "°C", "-10", "19.0 °C", "190"],
            ["2.18", "Air.Server-In.SetPtHighAlarm", "3", "°C", "-10", "35.0 °C", "350"],
            ["2.19", "Air.Server-In.SetPtHighWarning", "4", "°C", "-10", "30.0 °C", "300"],
            ["2.20", "Air.Server-In.SetPtLowWarning", "9", "°C", "-10", "15.0 °C", "150"],
            ["2.21", "Air.Server-In.SetPtLowAlarm", "5", "°C", "-10", "10.0 °C", "100"],
            ["2.22", "Air.Server-In.Hysteresis", "6", "%", "1", "5 %", "5"],
            ["2.23", "Air.Server-In.Status", "7", "", "0", "OK", "4"],
            ["2.24", "Air.Server-In.Category", "14", "", "0", "2", "2"],
            ["2.25", "Air.Server-Out.DescName", "1", "", "0", "Server-Out", "0"],
            ["2.26", "Air.Server-Out.Average", "2", "°C", "-10", "18.9 °C", "189"],
            ["2.27", "Air.Server-Out.SetPtHighAlarm", "3", "°C", "-10", "35.0 °C", "350"],
            ["2.28", "Air.Server-Out.SetPtHighWarning", "4", "°C", "-10", "30.0 °C", "300"],
            ["2.29", "Air.Server-Out.SetPtLowWarning", "9", "°C", "-10", "15.0 °C", "150"],
            ["2.30", "Air.Server-Out.SetPtLowAlarm", "5", "°C", "-10", "10.0 °C", "100"],
            ["2.31", "Air.Server-Out.Hysteresis", "6", "%", "1", "5 %", "5"],
            ["2.32", "Air.Server-Out.Status", "7", "", "0", "OK", "4"],
            ["2.33", "Air.Server-Out.Category", "14", "", "0", "2", "2"],
            ["2.34", "Air.Fans.All-Fans.SetPtLowWarning", "4", "%", "1", "14 %", "14"],
            ["2.35", "Air.Fans.Fan1.DescName", "1", "", "0", "Fan1", "0"],
            ["2.36", "Air.Fans.Fan1.Rpm", "2", "%", "1", "19 %", "19"],
            ["2.37", "Air.Fans.Fan1.Status", "7", "", "0", "OK", "4"],
            ["2.38", "Air.Fans.Fan1.Category", "14", "", "0", "2", "2"],
            ["2.39", "Air.Fans.Fan2.DescName", "1", "", "0", "Fan2", "0"],
            ["2.40", "Air.Fans.Fan2.Rpm", "2", "%", "1", "19 %", "19"],
            ["2.41", "Air.Fans.Fan2.Status", "7", "", "0", "OK", "4"],
            ["2.42", "Air.Fans.Fan2.Category", "14", "", "0", "2", "2"],
            ["2.43", "Air.Fans.Fan3.DescName", "1", "", "0", "Fan3", "0"],
            ["2.44", "Air.Fans.Fan3.Rpm", "2", "%", "1", "19 %", "19"],
            ["2.45", "Air.Fans.Fan3.Status", "7", "", "0", "OK", "4"],
            ["2.46", "Air.Fans.Fan3.Category", "14", "", "0", "2", "2"],
            ["2.47", "Air.Fans.Fan4.DescName", "1", "", "0", "Fan4", "0"],
            ["2.48", "Air.Fans.Fan4.Rpm", "2", "%", "1", "19 %", "19"],
            ["2.49", "Air.Fans.Fan4.Status", "7", "", "0", "OK", "4"],
            ["2.50", "Air.Fans.Fan4.Category", "14", "", "0", "2", "2"],
        ],
    ]  # yapf: disable


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize(
    "plugin,expected",
    [
        (
            "cmciii_temp_in_out",
            [
                Service(item="Air LCP In Bottom", parameters={"_item_key": "Air LCP In Bottom"}),
                Service(item="Air LCP In Middle", parameters={"_item_key": "Air LCP In Middle"}),
                Service(item="Air LCP In Top", parameters={"_item_key": "Air LCP In Top"}),
                Service(item="Air LCP Out Bottom", parameters={"_item_key": "Air LCP Out Bottom"}),
                Service(item="Air LCP Out Middle", parameters={"_item_key": "Air LCP Out Middle"}),
                Service(item="Air LCP Out Top", parameters={"_item_key": "Air LCP Out Top"}),
            ],
        ),
        (
            "cmciii_temp",
            [],
        ),
    ],
)
def test_cmciii_lcp_discovery(plugin, expected) -> None:
    assert run_discovery("cmciii", plugin, _lcp_sensor(), params={}) == expected


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize(
    "item, expected",
    [
        (
            "Air LCP In Bottom",
            [
                Metric("temp", 18.2),
                Result(state=State.OK, summary="Temperature: 18.2°C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (no levels found)",
                ),
            ],
        ),
        (
            "Air LCP In Middle",
            [
                Metric("temp", 19.0),
                Result(state=State.OK, summary="Temperature: 19.0°C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (no levels found)",
                ),
            ],
        ),
        (
            "Air LCP In Top",
            [
                Metric("temp", 19.8),
                Result(state=State.OK, summary="Temperature: 19.8°C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (no levels found)",
                ),
            ],
        ),
    ],
)
def test_cmciii_lcp_check(item, expected) -> None:
    assert run_check("cmciii", "cmciii_temp_in_out", item, _lcp_sensor(), params={}) == expected


def _phase_sensor():
    return [
        [["1", "PDU-MET", "Master PDU", "2"]],
        [
            ["1.1", "Unit.Frequency.Value", "2", "Hz", "-10", "50.0 Hz", "500"],
            ["1.2", "Unit.Neutral Current.DescName", "1", "", "0", "Neutral Current", "0"],
            ["1.3", "Unit.Neutral Current.Value", "2", "A", "-100", "3.05 A", "305"],
            ["1.4", "Unit.Neutral Current.SetPtHighAlarm", "3", "A", "-100", "0.00 A", "0"],
            ["1.5", "Unit.Neutral Current.SetPtHighWarning", "4", "A", "-100", "0.00 A", "0"],
            ["1.6", "Unit.Neutral Current.SetPtLowWarning", "9", "A", "-100", "0.00 A", "0"],
            ["1.7", "Unit.Neutral Current.SetPtLowAlarm", "5", "A", "-100", "0.00 A", "0"],
            ["1.8", "Unit.Neutral Current.Hysteresis", "6", "%", "-10", "1.0 %", "10"],
            ["1.9", "Unit.Neutral Current.Status", "7", "", "0", "OK", "4"],
            ["1.10", "Unit.Neutral Current.Category", "14", "", "0", "4", "4"],
            ["1.11", "Unit.Power.Active.DescName", "1", "", "0", "Power Active", "0"],
            ["1.12", "Unit.Power.Active.Value", "2", "W", "1", "1637 W", "1639"],
            ["1.13", "Unit.Power.Active.SetPtHighAlarm", "3", "W", "1", "0 W", "0"],
            ["1.14", "Unit.Power.Active.SetPtHighWarning", "4", "W", "1", "0 W", "0"],
            ["1.15", "Unit.Power.Active.SetPtLowWarning", "9", "W", "1", "0 W", "0"],
            ["1.16", "Unit.Power.Active.SetPtLowAlarm", "5", "W", "1", "0 W", "0"],
            ["1.17", "Unit.Power.Active.Hysteresis", "6", "%", "-10", "1.0 %", "10"],
            ["1.18", "Unit.Power.Active.Status", "7", "", "0", "OK", "4"],
            ["1.19", "Unit.Power.Active.Category", "14", "", "0", "4", "4"],
            ["1.20", "Unit.Energy.Active.Value", "2", "kWh", "-10", "7636.5 kWh", "76365"],
            ["1.21", "Unit.Energy.Active.Runtime.Value", "2", "s", "1", "18457906 s", "18457907"],
            ["1.22", "Unit.Energy.Active Custom.Value", "2", "kWh", "-10", "7636.5 kWh", "76365"],
            [
                "1.23",
                "Unit.Energy.Active Custom.Runtime.Value",
                "2",
                "s",
                "1",
                "18457906 s",
                "18457907",
            ],
            ["1.24", "Unit.Mounting Position", "93", "", "0", "Vertical up", "1"],
            ["1.25", "Phase L1.Voltage.DescName", "1", "", "0", "L1 Voltage", "0"],
            ["1.26", "Phase L1.Voltage.Value", "2", "V", "-10", "229.8 V", "2299"],
            ["1.27", "Phase L1.Voltage.SetPtHighAlarm", "3", "V", "-10", "260.0 V", "2600"],
            ["1.28", "Phase L1.Voltage.SetPtHighWarning", "4", "V", "-10", "260.0 V", "2600"],
            ["1.29", "Phase L1.Voltage.SetPtLowWarning", "9", "V", "-10", "0.0 V", "0"],
            ["1.30", "Phase L1.Voltage.SetPtLowAlarm", "5", "V", "-10", "0.0 V", "0"],
            ["1.31", "Phase L1.Voltage.Hysteresis", "6", "%", "-10", "1.0 %", "10"],
            ["1.32", "Phase L1.Voltage.Status", "7", "", "0", "OK", "4"],
            ["1.33", "Phase L1.Voltage.Category", "14", "", "0", "4", "4"],
            ["1.34", "Phase L1.Current.DescName", "1", "", "0", "L1 Current", "0"],
            ["1.35", "Phase L1.Current.Value", "2", "A", "-100", "4.44 A", "445"],
            ["1.36", "Phase L1.Current.SetPtHighAlarm", "3", "A", "-100", "0.00 A", "0"],
            ["1.37", "Phase L1.Current.SetPtHighWarning", "4", "A", "-100", "0.00 A", "0"],
            ["1.38", "Phase L1.Current.SetPtLowWarning", "9", "A", "-100", "0.00 A", "0"],
            ["1.39", "Phase L1.Current.SetPtLowAlarm", "5", "A", "-100", "0.00 A", "0"],
            ["1.40", "Phase L1.Current.Hysteresis", "6", "%", "-10", "1.0 %", "10"],
            ["1.41", "Phase L1.Current.Status", "7", "", "0", "OK", "4"],
            ["1.42", "Phase L1.Current.Category", "14", "", "0", "4", "4"],
            ["1.43", "Phase L1.Power.Factor.Value", "2", "", "-100", "1.00", "100"],
            ["1.44", "Phase L1.Power.Active.DescName", "1", "", "0", "L1 Power", "0"],
            ["1.45", "Phase L1.Power.Active.Value", "2", "W", "1", "1020 W", "1023"],
            ["1.46", "Phase L1.Power.Active.SetPtHighAlarm", "3", "W", "1", "0 W", "0"],
            ["1.47", "Phase L1.Power.Active.SetPtHighWarning", "4", "W", "1", "0 W", "0"],
            ["1.48", "Phase L1.Power.Active.SetPtLowWarning", "9", "W", "1", "0 W", "0"],
            ["1.49", "Phase L1.Power.Active.SetPtLowAlarm", "5", "W", "1", "0 W", "0"],
            ["1.50", "Phase L1.Power.Active.Hysteresis", "6", "%", "-10", "1.0 %", "10"],
            ["1.51", "Phase L1.Power.Active.Status", "7", "", "0", "OK", "4"],
            ["1.52", "Phase L1.Power.Active.Category", "14", "", "0", "4", "4"],
            ["1.53", "Phase L1.Power.Reactive.Value", "2", "var", "1", "11 var", "10"],
            ["1.54", "Phase L1.Power.Apparent.Value", "2", "VA", "1", "1020 VA", "1023"],
            ["1.55", "Phase L1.Energy.Active.Value", "2", "kWh", "-10", "4772.2 kWh", "47722"],
            [
                "1.56",
                "Phase L1.Energy.Active Custom.Value",
                "2",
                "kWh",
                "-10",
                "4772.2 kWh",
                "47722",
            ],
            ["1.57", "Phase L1.Energy.Apparent.Value", "2", "kVAh", "-10", "4871.2 kVAh", "48712"],
            ["1.58", "Phase L2.Voltage.DescName", "1", "", "0", "L2 Voltage", "0"],
            ["1.59", "Phase L2.Voltage.Value", "2", "V", "-10", "230.2 V", "2302"],
            ["1.60", "Phase L2.Voltage.SetPtHighAlarm", "3", "V", "-10", "260.0 V", "2600"],
            ["1.61", "Phase L2.Voltage.SetPtHighWarning", "4", "V", "-10", "260.0 V", "2600"],
            ["1.62", "Phase L2.Voltage.SetPtLowWarning", "9", "V", "-10", "0.0 V", "0"],
            ["1.63", "Phase L2.Voltage.SetPtLowAlarm", "5", "V", "-10", "0.0 V", "0"],
            ["1.64", "Phase L2.Voltage.Hysteresis", "6", "%", "-10", "1.0 %", "10"],
            ["1.65", "Phase L2.Voltage.Status", "7", "", "0", "OK", "4"],
            ["1.66", "Phase L2.Voltage.Category", "14", "", "0", "4", "4"],
            ["1.67", "Phase L2.Current.DescName", "1", "", "0", "L2 Current", "0"],
            ["1.68", "Phase L2.Current.Value", "2", "A", "-100", "1.54 A", "154"],
            ["1.69", "Phase L2.Current.SetPtHighAlarm", "3", "A", "-100", "0.00 A", "0"],
            ["1.70", "Phase L2.Current.SetPtHighWarning", "4", "A", "-100", "0.00 A", "0"],
            ["1.71", "Phase L2.Current.SetPtLowWarning", "9", "A", "-100", "0.00 A", "0"],
            ["1.72", "Phase L2.Current.SetPtLowAlarm", "5", "A", "-100", "0.00 A", "0"],
            ["1.73", "Phase L2.Current.Hysteresis", "6", "%", "-10", "1.0 %", "10"],
            ["1.74", "Phase L2.Current.Status", "7", "", "0", "OK", "4"],
            ["1.75", "Phase L2.Current.Category", "14", "", "0", "4", "4"],
            ["1.76", "Phase L2.Power.Factor.Value", "2", "", "-100", "0.87", "88"],
            ["1.77", "Phase L2.Power.Active.DescName", "1", "", "0", "L2 Power", "0"],
            ["1.78", "Phase L2.Power.Active.Value", "2", "W", "1", "310 W", "311"],
            ["1.79", "Phase L2.Power.Active.SetPtHighAlarm", "3", "W", "1", "0 W", "0"],
            ["1.80", "Phase L2.Power.Active.SetPtHighWarning", "4", "W", "1", "0 W", "0"],
            ["1.81", "Phase L2.Power.Active.SetPtLowWarning", "9", "W", "1", "0 W", "0"],
            ["1.82", "Phase L2.Power.Active.SetPtLowAlarm", "5", "W", "1", "0 W", "0"],
            ["1.83", "Phase L2.Power.Active.Hysteresis", "6", "%", "-10", "1.0 %", "10"],
            ["1.84", "Phase L2.Power.Active.Status", "7", "", "0", "OK", "4"],
            ["1.85", "Phase L2.Power.Active.Category", "14", "", "0", "4", "4"],
            ["1.86", "Phase L2.Power.Reactive.Value", "2", "var", "1", "174 var", "172"],
            ["1.87", "Phase L2.Power.Apparent.Value", "2", "VA", "1", "355 VA", "355"],
            ["1.88", "Phase L2.Energy.Active.Value", "2", "kWh", "-10", "1378.6 kWh", "13786"],
            [
                "1.89",
                "Phase L2.Energy.Active Custom.Value",
                "2",
                "kWh",
                "-10",
                "1378.6 kWh",
                "13786",
            ],
            ["1.90", "Phase L2.Energy.Apparent.Value", "2", "kVAh", "-10", "1541.5 kVAh", "15415"],
            ["1.91", "Phase L3.Voltage.DescName", "1", "", "0", "L3 Voltage", "0"],
            ["1.92", "Phase L3.Voltage.Value", "2", "V", "-10", "230.2 V", "2302"],
            ["1.93", "Phase L3.Voltage.SetPtHighAlarm", "3", "V", "-10", "260.0 V", "2600"],
            ["1.94", "Phase L3.Voltage.SetPtHighWarning", "4", "V", "-10", "260.0 V", "2600"],
            ["1.95", "Phase L3.Voltage.SetPtLowWarning", "9", "V", "-10", "0.0 V", "0"],
            ["1.96", "Phase L3.Voltage.SetPtLowAlarm", "5", "V", "-10", "0.0 V", "0"],
            ["1.97", "Phase L3.Voltage.Hysteresis", "6", "%", "-10", "1.0 %", "10"],
            ["1.98", "Phase L3.Voltage.Status", "7", "", "0", "OK", "4"],
            ["1.99", "Phase L3.Voltage.Category", "14", "", "0", "4", "4"],
            ["1.100", "Phase L3.Current.DescName", "1", "", "0", "L3 Current", "0"],
            ["1.101", "Phase L3.Current.Value", "2", "A", "-100", "1.62 A", "161"],
            ["1.102", "Phase L3.Current.SetPtHighAlarm", "3", "A", "-100", "0.00 A", "0"],
            ["1.103", "Phase L3.Current.SetPtHighWarning", "4", "A", "-100", "0.00 A", "0"],
            ["1.104", "Phase L3.Current.SetPtLowWarning", "9", "A", "-100", "0.00 A", "0"],
            ["1.105", "Phase L3.Current.SetPtLowAlarm", "5", "A", "-100", "0.00 A", "0"],
            ["1.106", "Phase L3.Current.Hysteresis", "6", "%", "-10", "1.0 %", "10"],
            ["1.107", "Phase L3.Current.Status", "7", "", "0", "OK", "4"],
            ["1.108", "Phase L3.Current.Category", "14", "", "0", "4", "4"],
            ["1.109", "Phase L3.Power.Factor.Value", "2", "", "-100", "0.82", "82"],
            ["1.110", "Phase L3.Power.Active.DescName", "1", "", "0", "L3 Power", "0"],
            ["1.111", "Phase L3.Power.Active.Value", "2", "W", "1", "305 W", "305"],
            ["1.112", "Phase L3.Power.Active.SetPtHighAlarm", "3", "W", "1", "0 W", "0"],
            ["1.113", "Phase L3.Power.Active.SetPtHighWarning", "4", "W", "1", "0 W", "0"],
            ["1.114", "Phase L3.Power.Active.SetPtLowWarning", "9", "W", "1", "0 W", "0"],
            ["1.115", "Phase L3.Power.Active.SetPtLowAlarm", "5", "W", "1", "0 W", "0"],
            ["1.116", "Phase L3.Power.Active.Hysteresis", "6", "%", "-10", "1.0 %", "10"],
            ["1.117", "Phase L3.Power.Active.Status", "7", "", "0", "OK", "4"],
            ["1.118", "Phase L3.Power.Active.Category", "14", "", "0", "4", "4"],
            ["1.119", "Phase L3.Power.Reactive.Value", "2", "var", "1", "211 var", "211"],
            ["1.120", "Phase L3.Power.Apparent.Value", "2", "VA", "1", "371 VA", "371"],
            ["1.121", "Phase L3.Energy.Active.Value", "2", "kWh", "-10", "1485.7 kWh", "14857"],
            [
                "1.122",
                "Phase L3.Energy.Active Custom.Value",
                "2",
                "kWh",
                "-10",
                "1485.7 kWh",
                "14857",
            ],
            ["1.123", "Phase L3.Energy.Apparent.Value", "2", "kVAh", "-10", "1816.4 kVAh", "18164"],
            ["1.124", "Memory.USB-Stick.DescName", "1", "", "0", "USB-Stick", "0"],
            ["1.125", "Memory.USB-Stick.Size", "2", "GB", "-10", "0.0 GB", "0"],
            ["1.126", "Memory.USB-Stick.Usage", "2", "%", "1", "0 %", "0"],
            ["1.127", "Memory.USB-Stick.Command", "81", "", "0", "--", "4"],
            ["1.128", "Memory.USB-Stick.Status", "7", "", "0", "n.a.", "1"],
            ["1.129", "Memory.USB-Stick.Category", "14", "", "1", "16", "16"],
        ],
    ]  # yapf: disable


def test_phase_sensors() -> None:
    params = {"use_sensor_description": False}
    section = cmciii.parse_cmciii(_phase_sensor())
    assert list(cmciii_phase.discover_cmciii_phase(params, section)) == [
        Service(item="Master_PDU Phase 1", parameters={"_item_key": "Master_PDU Phase 1"}),
        Service(item="Master_PDU Phase 2", parameters={"_item_key": "Master_PDU Phase 2"}),
        Service(item="Master_PDU Phase 3", parameters={"_item_key": "Master_PDU Phase 3"}),
    ]


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize(
    "item, expected",
    [
        (
            "Master_PDU Phase 1",
            [
                Result(state=State.OK, summary="Voltage: 229.9 V"),
                Metric("voltage", 229.9),
                Result(state=State.OK, summary="Current: 4.5 A"),
                Metric("current", 4.45),
                Result(state=State.OK, summary="Power: 1023.0 W"),
                Metric("power", 1023.0),
                Result(state=State.OK, summary="Apparent Power: 1023.0 VA"),
                Metric("appower", 1023.0),
                Result(state=State.OK, summary="Energy: 4772.2 Wh"),
                Metric("energy", 4772.2),
            ],
        ),
    ],
)
def test_cmciii_phase_check(item, expected) -> None:
    assert run_check("cmciii", "cmciii_phase", item, _phase_sensor(), params={}) == expected


def _status_info(variable, status):
    return [
        [["2", "CMCIII-DET-M", "DET-AC III Master", "2"]],
        [
            ["2.1", "%s.DescName" % variable, "1", "", "0", "Leakage", "0"],
            ["2.2", "%s.Status" % variable, "7", "", "0", status, "4"],
            ["2.3", "%s.Category" % variable, "14", "", "0", "80", "80"],
        ],
    ]


@pytest.mark.parametrize(
    "variable",
    [
        "External release",
        "Fire",
        "Extinguishing agent",
        "Extinguishing system",
        "Pre-Alarm",
        "Manual detector",
        "Manual release",
        "Door contact",
        "Air flow",
        "Detector 1",
        "Communication",
        "Battery",
        "Battery change",
        "Maintenance interval",
        "Mains",
        "Mains adapter",
        "Ignition",
    ],
)
def test_cmciii_status_discovery(variable) -> None:
    service_description = "DET-AC_III_Master %s" % variable
    params = {"use_sensor_description": False}
    section = cmciii.parse_cmciii(_status_info(variable, "OK"))
    assert list(cmciii_status.discover_cmciii_status(params, section)) == [
        Service(item=service_description, parameters={"_item_key": service_description})
    ]


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize(
    "variable, status, expected",
    [
        ("External release", "OK", [Result(state=State.OK, summary="Status: OK")]),
        ("Air flow", "Too Low", [Result(state=State.CRIT, summary="Status: Too Low")]),
        ("Battery change", "Service", [Result(state=State.CRIT, summary="Status: Service")]),
    ],
)
def test_cmciii_status_sensors(variable, status, expected) -> None:
    assert (
        run_check(
            "cmciii",
            "cmciii_status",
            "DET-AC_III_Master %s" % variable,
            _status_info(variable, status),
            params={},
        )
        == expected
    )


def _access_info():
    return [
        [["3", "CMCIII-GRF", "Tuer GN-31-F", "2"]],
        [
            ["3.1", "Access.DescName", "1", "", "0", "Access", "0"],
            ["3.2", "Access.Command", "81", "", "0", "Open", "6"],
            ["3.3", "Access.Value", "2", "", "1", "0", "0"],
            ["3.4", "Access.Sensitivity", "30", "", "1", "2", "2"],
            ["3.5", "Access.Delay", "21", "s", "1", "5 s", "5"],
            ["3.6", "Access.Status", "7", "", "0", "Closed", "13"],
            ["3.7", "Access.Category", "14", "", "0", "0", "0"],
        ],
    ]  # yapf: disable


@pytest.mark.usefixtures("fix_register")
def test_cmciii_access_discovery() -> None:
    assert run_discovery("cmciii", "cmciii_access", _access_info(), {}) == [
        Service(item="Tuer_GN-31-F Access", parameters={"_item_key": "Tuer_GN-31-F Access"})
    ]


@pytest.mark.usefixtures("fix_register")
def test_cmciii_access_check() -> None:
    assert run_check(
        "cmciii",
        "cmciii_access",
        "Tuer_GN-31-F Access",
        _access_info(),
        params={},
    ) == [
        Result(state=State.OK, summary="Access: Closed"),
        Result(state=State.OK, summary="Delay: 5 s"),
        Result(state=State.OK, summary="Sensitivity: 2.0"),
    ]


def _generictest_cmciii():
    return [
        [
            ["1", "CMCIII-PU", "CMC-PU", "2"],
            ["2", "CMCIII-IO3", "CMC-IOModul", "2"],
            ["3", "CMCIII-HUM", "CMC-Temperatur", "2"],
            ["4", "CMCIII-SMK", "CMC-Rauchmelder", "2"],
        ],
        [
            ["1.1", "Temperature.DescName", "1", "", "0", "Temperature", "0"],
            ["1.2", "Temperature.Value", "2", "degree C", "-100", "30.50 degree C", "3050"],
            ["1.3", "Temperature.Offset", "18", "degree C", "", "0.00 degree C", "0"],
            [
                "1.4",
                "Temperature.SetPtHighAlarm",
                "3",
                "degree C",
                "-100",
                "45.00 degree C",
                "4500",
            ],
            [
                "1.5",
                "Temperature.SetPtHighWarning",
                "4",
                "degree C",
                "-100",
                "40.00 degree C",
                "4000",
            ],
            [
                "1.6",
                "Temperature.SetPtLowWarning",
                "9",
                "degree C",
                "-100",
                "10.00 degree C",
                "1000",
            ],
            ["1.7", "Temperature.SetPtLowAlarm", "5", "degree C", "-100", "5.00 degree C", "500"],
            ["1.8", "Temperature.Hysteresis", "6", "%", "-100", "5.00 %", "500"],
            ["1.9", "Temperature.Status", "7", "", "0", "OK", "4"],
            ["1.10", "Temperature.Category", "14", "", "0", "16", "16"],
            ["1.11", "Access.DescName", "1", "", "0", "Door", "0"],
            ["1.12", "Access.Value", "2", "", "1", "0", "0"],
            ["1.13", "Access.Sensitivity", "30", "", "1", "0", "0"],
            ["1.14", "Access.Delay", "21", "s", "1", "10 s", "10"],
            ["1.15", "Access.Status", "7", "", "0", "Inactive", "27"],
            ["1.16", "Access.Category", "14", "", "0", "192", "192"],
            ["1.17", "Input 1.DescName", "1", "", "0", "Input_1", "0"],
            ["1.18", "Input 1.Value", "2", "", "1", "0", "0"],
            ["1.19", "Input 1.Logic", "15", "", "0", "0:Off / 1:On", "0"],
            ["1.20", "Input 1.Delay", "21", "s", "-10", "0.5 s", "5"],
            ["1.21", "Input 1.Status", "7", "", "0", "Off", "10"],
            ["1.22", "Input 1.Category", "14", "", "0", "16", "16"],
            ["1.23", "Input 2.DescName", "1", "", "0", "Input_2", "0"],
            ["1.24", "Input 2.Value", "2", "", "1", "0", "0"],
            ["1.25", "Input 2.Logic", "15", "", "0", "0:Off / 1:On", "0"],
            ["1.26", "Input 2.Delay", "21", "s", "-10", "0.5 s", "5"],
            ["1.27", "Input 2.Status", "7", "", "0", "Off", "10"],
            ["1.28", "Input 2.Category", "14", "", "0", "16", "16"],
            ["1.29", "Output.DescName", "1", "", "0", "Alarm Relay", "0"],
            ["1.30", "Output.Relay", "20", "", "0", "Off", "0"],
            ["1.31", "Output.Logic", "15", "", "0", "0:Off / 1:On", "0"],
            ["1.32", "Output.Status", "7", "", "0", "Off", "10"],
            ["1.33", "Output.Category", "14", "", "0", "16", "16"],
            ["1.34", "System.V24 Port.DescName", "1", "", "0", "V24 Unit", "0"],
            ["1.35", "System.V24 Port.Message", "95", "", "0", "no SMS unit found", "0"],
            ["1.36", "System.V24 Port.Signal", "2", "%", "1", "0 %", "0"],
            ["1.37", "System.V24 Port.Status", "7", "", "0", "n.a.", "1"],
            ["1.38", "System.V24 Port.Category", "14", "", "0", "16", "16"],
            ["1.39", "System.CAN1 Current.DescName", "1", "", "0", "CAN1 Current", "0"],
            ["1.40", "System.CAN1 Current.Value", "2", "mA", "1", "0 mA", "0"],
            ["1.41", "System.CAN1 Current.SetPtHighAlarm", "3", "mA", "1", "900 mA", "900"],
            ["1.42", "System.CAN1 Current.SetPtHighWarning", "4", "mA", "1", "700 mA", "700"],
            ["1.43", "System.CAN1 Current.Hysteresis", "6", "%", "-100", "5.00 %", "500"],
            ["1.44", "System.CAN1 Current.Status", "7", "", "0", "OK", "4"],
            ["1.45", "System.CAN1 Current.Category", "14", "", "0", "16", "16"],
            ["1.46", "System.CAN2 Current.DescName", "1", "", "0", "CAN2 Current", "0"],
            ["1.47", "System.CAN2 Current.Value", "2", "mA", "1", "0 mA", "0"],
            ["1.48", "System.CAN2 Current.SetPtHighAlarm", "3", "mA", "1", "900 mA", "900"],
            ["1.49", "System.CAN2 Current.SetPtHighWarning", "4", "mA", "1", "700 mA", "700"],
            ["1.50", "System.CAN2 Current.Hysteresis", "6", "%", "-100", "5.00 %", "500"],
            ["1.51", "System.CAN2 Current.Status", "7", "", "0", "OK", "4"],
            ["1.52", "System.CAN2 Current.Category", "14", "", "0", "16", "16"],
            ["1.53", "System.Temperature.DescName", "1", "", "0", "Sys Temp", "0"],
            ["1.54", "System.Temperature.Value", "2", "degree C", "-100", "32.30 degree C", "3230"],
            ["1.55", "System.Temperature.Offset", "18", "degree C", "-100", "0.00 degree C", "0"],
            [
                "1.56",
                "System.Temperature.SetPtHighAlarm",
                "3",
                "degree C",
                "-100",
                "80.00 degree C",
                "8000",
            ],
            [
                "1.57",
                "System.Temperature.SetPtHighWarning",
                "4",
                "degree C",
                "-100",
                "70.00 degree C",
                "7000",
            ],
            [
                "1.58",
                "System.Temperature.SetPtLowWarning",
                "9",
                "degree C",
                "-100",
                "-25.00 degree C",
                "-2500",
            ],
            [
                "1.59",
                "System.Temperature.SetPtLowAlarm",
                "5",
                "degree C",
                "-100",
                "-30.00 degree C",
                "-3000",
            ],
            ["1.60", "System.Temperature.Hysteresis", "6", "%", "-100", "10.00 %", "1000"],
            ["1.61", "System.Temperature.Status", "7", "", "0", "OK", "4"],
            ["1.62", "System.Temperature.Category", "14", "", "0", "16", "16"],
            ["1.63", "System.Supply 24V.DescName", "1", "", "0", "Supply 24V", "0"],
            ["1.64", "System.Supply 24V.Value", "2", "V", "-1000", "23.510 V", "23510"],
            ["1.65", "System.Supply 24V.SetPtHighAlarm", "3", "V", "-1000", "28.000 V", "28000"],
            ["1.66", "System.Supply 24V.SetPtHighWarning", "4", "V", "-1000", "26.000 V", "26000"],
            ["1.67", "System.Supply 24V.SetPtLowWarning", "9", "V", "-1000", "21.000 V", "21000"],
            ["1.68", "System.Supply 24V.SetPtLowAlarm", "5", "V", "-1000", "19.000 V", "19000"],
            ["1.69", "System.Supply 24V.Hysteresis", "6", "%", "-100", "10.00 %", "1000"],
            ["1.70", "System.Supply 24V.Status", "7", "", "0", "OK", "4"],
            ["1.71", "System.Supply 24V.Category", "14", "", "0", "16", "16"],
            ["1.72", "System.Supply 5V0.DescName", "1", "", "0", "Supply 5V0", "0"],
            ["1.73", "System.Supply 5V0.Value", "2", "V", "-1000", "5.000 V", "5000"],
            ["1.74", "System.Supply 5V0.SetPtHighAlarm", "3", "V", "-1000", "5.500 V", "5500"],
            ["1.75", "System.Supply 5V0.SetPtHighWarning", "4", "V", "-1000", "5.400 V", "5400"],
            ["1.76", "System.Supply 5V0.SetPtLowWarning", "9", "V", "-1000", "4.600 V", "4600"],
            ["1.77", "System.Supply 5V0.SetPtLowAlarm", "5", "V", "-1000", "4.500 V", "4500"],
            ["1.78", "System.Supply 5V0.Hysteresis", "6", "%", "-100", "2.00 %", "200"],
            ["1.79", "System.Supply 5V0.Status", "7", "", "0", "OK", "4"],
            ["1.80", "System.Supply 5V0.Category", "14", "", "0", "16", "16"],
            ["1.81", "System.Supply 3V3.DescName", "1", "", "0", "Supply 3V3", "0"],
            ["1.82", "System.Supply 3V3.Value", "2", "V", "-1000", "3.290 V", "3290"],
            ["1.83", "System.Supply 3V3.SetPtHighAlarm", "3", "V", "-1000", "3.630 V", "3630"],
            ["1.84", "System.Supply 3V3.SetPtHighWarning", "4", "V", "-1000", "3.560 V", "3560"],
            ["1.85", "System.Supply 3V3.SetPtLowWarning", "9", "V", "-1000", "3.040 V", "3040"],
            ["1.86", "System.Supply 3V3.SetPtLowAlarm", "5", "V", "-1000", "2.970 V", "2970"],
            ["1.87", "System.Supply 3V3.Hysteresis", "6", "%", "-100", "2.00 %", "200"],
            ["1.88", "System.Supply 3V3.Status", "7", "", "0", "OK", "4"],
            ["1.89", "System.Supply 3V3.Category", "14", "", "0", "16", "16"],
            ["1.90", "Memory.USB-Stick.DescName", "1", "", "0", "USB-Stick", "0"],
            ["1.91", "Memory.USB-Stick.Size", "2", "GB", "-10", "0.0 GB", "0"],
            ["1.92", "Memory.USB-Stick.Usage", "2", "%", "1", "0 %", "0"],
            ["1.93", "Memory.USB-Stick.Command", "81", "", "0", "--", "4"],
            ["1.94", "Memory.USB-Stick.Status", "7", "", "0", "n.a.", "1"],
            ["1.95", "Memory.USB-Stick.Category", "14", "", "0", "16", "16"],
            ["1.96", "Memory.SD-Card.DescName", "1", "", "0", "SD-Card", "0"],
            ["1.97", "Memory.SD-Card.Size", "2", "GB", "-10", "0.0 GB", "0"],
            ["1.98", "Memory.SD-Card.Usage", "2", "%", "1", "0 %", "0"],
            ["1.99", "Memory.SD-Card.Command", "81", "", "0", "--", "4"],
            ["1.100", "Memory.SD-Card.Status", "7", "", "0", "n.a.", "1"],
            ["1.101", "Memory.SD-Card.Category", "14", "", "0", "16", "16"],
            ["1.102", "Webcam.DescName", "1", "", "0", "Webcam", "0"],
            ["1.103", "Webcam.Command", "81", "", "0", "--", "4"],
            ["1.104", "Webcam.Status", "7", "", "0", "n.a.", "1"],
            ["1.105", "Webcam.Category", "14", "", "0", "16", "16"],
            ["2.1", "Input 1.DescName", "1", "", "0", "Super Input", "0"],
            ["2.2", "Input 1.Value", "2", "", "1", "0", "0"],
            ["2.3", "Input 1.Logic", "15", "", "0", "0:OK / 1:Alarm", "2"],
            ["2.4", "Input 1.Delay", "21", "s", "-10", "5.0 s", "50"],
            ["2.5", "Input 1.Status", "7", "", "0", "OK", "4"],
            ["2.6", "Input 1.Category", "14", "", "0", "0", "0"],
            ["2.7", "Input 2.DescName", "1", "", "0", "Duper Input", "0"],
            ["2.8", "Input 2.Value", "2", "", "1", "0", "0"],
            ["2.9", "Input 2.Logic", "15", "", "0", "0:OK / 1:Alarm", "2"],
            ["2.10", "Input 2.Delay", "21", "s", "-10", "5.0 s", "50"],
            ["2.11", "Input 2.Status", "7", "", "0", "OK", "4"],
            ["2.12", "Input 2.Category", "14", "", "0", "0", "0"],
            ["2.13", "Input 3.DescName", "1", "", "0", "Blitzschutz", "0"],
            ["2.14", "Input 3.Value", "2", "", "1", "1", "1"],
            ["2.15", "Input 3.Logic", "15", "", "0", "0:On / 1:Off", "1"],
            ["2.16", "Input 3.Delay", "21", "s", "-10", "5.0 s", "50"],
            ["2.17", "Input 3.Status", "7", "", "0", "Off", "10"],
            ["2.18", "Input 3.Category", "14", "", "0", "0", "0"],
            ["2.19", "Input 4.DescName", "1", "", "0", "Rote Tuer", "0"],
            ["2.20", "Input 4.Value", "2", "", "1", "1", "1"],
            ["2.21", "Input 4.Logic", "15", "", "0", "0:Alarm / 1:OK", "3"],
            ["2.22", "Input 4.Delay", "21", "s", "-10", "0.5 s", "5"],
            ["2.23", "Input 4.Status", "7", "", "0", "OK", "4"],
            ["2.24", "Input 4.Category", "14", "", "0", "0", "0"],
            ["2.25", "Input 5.DescName", "1", "", "0", "Gelbe Tuer", "0"],
            ["2.26", "Input 5.Value", "2", "", "1", "1", "1"],
            ["2.27", "Input 5.Logic", "15", "", "0", "0:Alarm / 1:OK", "3"],
            ["2.28", "Input 5.Delay", "21", "s", "-10", "0.5 s", "5"],
            ["2.29", "Input 5.Status", "7", "", "0", "OK", "4"],
            ["2.30", "Input 5.Category", "14", "", "0", "0", "0"],
            ["2.31", "Input 6.DescName", "1", "", "0", "Gruene Tuer", "0"],
            ["2.32", "Input 6.Value", "2", "", "1", "1", "1"],
            ["2.33", "Input 6.Logic", "15", "", "0", "0:Alarm / 1:OK", "3"],
            ["2.34", "Input 6.Delay", "21", "s", "-10", "0.5 s", "5"],
            ["2.35", "Input 6.Status", "7", "", "0", "OK", "4"],
            ["2.36", "Input 6.Category", "14", "", "0", "0", "0"],
            ["2.37", "Input 7.DescName", "1", "", "0", "Input_7", "0"],
            ["2.38", "Input 7.Value", "2", "", "1", "0", "0"],
            ["2.39", "Input 7.Logic", "15", "", "0", "0:Off / 1:On", "0"],
            ["2.40", "Input 7.Delay", "21", "s", "-10", "0.5 s", "5"],
            ["2.41", "Input 7.Status", "7", "", "0", "Off", "10"],
            ["2.42", "Input 7.Category", "14", "", "0", "0", "0"],
            ["2.43", "Input 8.DescName", "1", "", "0", "Input_8", "0"],
            ["2.44", "Input 8.Value", "2", "", "1", "0", "0"],
            ["2.45", "Input 8.Logic", "15", "", "0", "0:Off / 1:On", "0"],
            ["2.46", "Input 8.Delay", "21", "s", "-10", "0.5 s", "5"],
            ["2.47", "Input 8.Status", "7", "", "0", "Off", "10"],
            ["2.48", "Input 8.Category", "14", "", "0", "0", "0"],
            ["2.49", "Output 1.DescName", "1", "", "0", "Maxihub", "0"],
            ["2.50", "Output 1.Relay", "20", "", "0", "Off", "0"],
            ["2.51", "Output 1.Grouping", "100", "", "0", "0", "0"],
            ["2.52", "Output 1.Logic", "15", "", "0", "0:OK / 1:Alarm", "2"],
            ["2.53", "Output 1.Status", "7", "", "0", "OK", "4"],
            ["2.54", "Output 1.Category", "14", "", "0", "0", "0"],
            ["2.55", "Output 2.DescName", "1", "", "0", "Output_2", "0"],
            ["2.56", "Output 2.Relay", "20", "", "0", "Off", "0"],
            ["2.57", "Output 2.Grouping", "100", "", "0", "0", "0"],
            ["2.58", "Output 2.Logic", "15", "", "0", "0:OK / 1:Alarm", "2"],
            ["2.59", "Output 2.Status", "7", "", "0", "OK", "4"],
            ["2.60", "Output 2.Category", "14", "", "0", "0", "0"],
            ["2.61", "Output 3.DescName", "1", "", "0", "Output_3", "0"],
            ["2.62", "Output 3.Relay", "20", "", "0", "Off", "0"],
            ["2.63", "Output 3.Grouping", "100", "", "0", "0", "0"],
            ["2.64", "Output 3.Logic", "15", "", "0", "0:OK / 1:Alarm", "2"],
            ["2.65", "Output 3.Status", "7", "", "0", "OK", "4"],
            ["2.66", "Output 3.Category", "14", "", "0", "0", "0"],
            ["2.67", "Output 4.DescName", "1", "", "0", "Output_4", "0"],
            ["2.68", "Output 4.Relay", "20", "", "0", "Off", "0"],
            ["2.69", "Output 4.Grouping", "100", "", "0", "0", "0"],
            ["2.70", "Output 4.Logic", "15", "", "0", "0:OK / 1:Alarm", "2"],
            ["2.71", "Output 4.Status", "7", "", "0", "OK", "4"],
            ["2.72", "Output 4.Category", "14", "", "0", "0", "0"],
            ["3.1", "Temperature.DescName", "1", "", "0", "Temperature", "0"],
            ["3.2", "Temperature.Value", "2", "degree C", "-100", "27.00 degree C", "2700"],
            ["3.3", "Temperature.Offset", "18", "degree C", "-100", "0.00 degree C", "0"],
            [
                "3.4",
                "Temperature.SetPtHighAlarm",
                "3",
                "degree C",
                "-100",
                "40.00 degree C",
                "4000",
            ],
            [
                "3.5",
                "Temperature.SetPtHighWarning",
                "4",
                "degree C",
                "-100",
                "35.00 degree C",
                "3500",
            ],
            [
                "3.6",
                "Temperature.SetPtLowWarning",
                "9",
                "degree C",
                "-100",
                "10.00 degree C",
                "1000",
            ],
            ["3.7", "Temperature.SetPtLowAlarm", "5", "degree C", "-100", "5.00 degree C", "500"],
            ["3.8", "Temperature.Hysteresis", "6", "%", "-100", "0.00 %", "0"],
            ["3.9", "Temperature.Status", "7", "", "0", "OK", "4"],
            ["3.10", "Temperature.Category", "14", "", "0", "80", "80"],
            ["3.11", "Humidity.DescName", "1", "", "0", "Humidity", "0"],
            ["3.12", "Humidity.Value", "2", "%", "-100", "9.50 %", "950"],
            ["3.13", "Humidity.Offset", "18", "%", "-100", "0.00 %", "0"],
            ["3.14", "Humidity.SetPtHighAlarm", "3", "%", "-100", "80.00 %", "8000"],
            ["3.15", "Humidity.SetPtHighWarning", "4", "%", "-100", "75.00 %", "7500"],
            ["3.16", "Humidity.SetPtLowWarning", "9", "%", "-100", "10.00 %", "1000"],
            ["3.17", "Humidity.SetPtLowAlarm", "5", "%", "-100", "5.00 %", "500"],
            ["3.18", "Humidity.Hysteresis", "6", "%", "-100", "0.00 %", "0"],
            ["3.19", "Humidity.Status", "7", "", "0", "Low Warn", "9"],
            ["3.20", "Humidity.Category", "14", "", "0", "80", "80"],
            ["3.21", "Dew Point.DescName", "1", "", "0", "Dew Point", "0"],
            ["3.22", "Dew Point.Value", "2", "degree C", "-100", "-7.80 degree C", "-780"],
            ["4.1", "Smoke.DescName", "1", "", "0", "Rauchmelder", "0"],
            ["4.2", "Smoke.Value", "2", "", "1", "0", "0"],
            ["4.3", "Smoke.Delay", "21", "s", "1", "0 s", "0"],
            ["4.4", "Smoke.Status", "7", "", "0", "OK", "4"],
            ["4.5", "Smoke.Category", "14", "", "0", "80", "80"],
        ],
    ]  # yapf: disable


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize(
    "plugin,params,expected",
    [
        (
            "cmciii",
            {},
            [
                Service(item="CMC-IOModul", parameters={"_item_key": "CMC-IOModul"}),
                Service(item="CMC-PU", parameters={"_item_key": "CMC-PU"}),
                Service(item="CMC-Rauchmelder", parameters={"_item_key": "CMC-Rauchmelder"}),
                Service(item="CMC-Temperatur", parameters={"_item_key": "CMC-Temperatur"}),
            ],
        ),
        ("cmciii_psm_current", {}, []),
        ("cmciii_psm_plugs", {}, []),
        (
            "cmciii_io",
            {},
            [
                Service(
                    item="CMC-IOModul Input 1", parameters={"_item_key": "CMC-IOModul Input 1"}
                ),
                Service(
                    item="CMC-IOModul Input 2", parameters={"_item_key": "CMC-IOModul Input 2"}
                ),
                Service(
                    item="CMC-IOModul Input 3", parameters={"_item_key": "CMC-IOModul Input 3"}
                ),
                Service(
                    item="CMC-IOModul Input 4", parameters={"_item_key": "CMC-IOModul Input 4"}
                ),
                Service(
                    item="CMC-IOModul Input 5", parameters={"_item_key": "CMC-IOModul Input 5"}
                ),
                Service(
                    item="CMC-IOModul Input 6", parameters={"_item_key": "CMC-IOModul Input 6"}
                ),
                Service(
                    item="CMC-IOModul Input 7", parameters={"_item_key": "CMC-IOModul Input 7"}
                ),
                Service(
                    item="CMC-IOModul Input 8", parameters={"_item_key": "CMC-IOModul Input 8"}
                ),
                Service(
                    item="CMC-IOModul Output 1", parameters={"_item_key": "CMC-IOModul Output 1"}
                ),
                Service(
                    item="CMC-IOModul Output 2", parameters={"_item_key": "CMC-IOModul Output 2"}
                ),
                Service(
                    item="CMC-IOModul Output 3", parameters={"_item_key": "CMC-IOModul Output 3"}
                ),
                Service(
                    item="CMC-IOModul Output 4", parameters={"_item_key": "CMC-IOModul Output 4"}
                ),
                Service(item="CMC-PU Input 1", parameters={"_item_key": "CMC-PU Input 1"}),
                Service(item="CMC-PU Input 2", parameters={"_item_key": "CMC-PU Input 2"}),
                Service(item="CMC-PU Output", parameters={"_item_key": "CMC-PU Output"}),
            ],
        ),
        (
            "cmciii_access",
            {},
            [Service(item="CMC-PU Access", parameters={"_item_key": "CMC-PU Access"})],
        ),
        (
            "cmciii_temp",
            {},
            [
                Service(item="Ambient CMC-PU", parameters={"_item_key": "Ambient CMC-PU"}),
                Service(
                    item="Ambient CMC-Temperatur",
                    parameters={"_item_key": "Ambient CMC-Temperatur"},
                ),
                Service(
                    item="Dew Point CMC-Temperatur",
                    parameters={"_item_key": "Dew Point CMC-Temperatur"},
                ),
                Service(item="System CMC-PU", parameters={"_item_key": "System CMC-PU"}),
            ],
        ),
        ("cmciii_temp_in_out", {}, []),
        (
            "cmciii_can_current",
            {},
            [
                Service(
                    item="CMC-PU System.CAN1 Current",
                    parameters={"_item_key": "CMC-PU System.CAN1 Current"},
                ),
                Service(
                    item="CMC-PU System.CAN2 Current",
                    parameters={"_item_key": "CMC-PU System.CAN2 Current"},
                ),
            ],
        ),
        (
            "cmciii_humidity",
            {},
            [
                Service(
                    item="CMC-Temperatur Humidity",
                    parameters={"_item_key": "CMC-Temperatur Humidity"},
                )
            ],
        ),
        ("cmciii_phase", {}, []),
    ],
)
def test_genericdataset_cmciii_discovery(plugin, params, expected) -> None:
    assert run_discovery("cmciii", plugin, _generictest_cmciii(), params) == expected


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize(
    "plugin, params, items",
    [
        (
            "cmciii",
            {},
            [
                ("CMC-IOModul", [Result(state=State.OK, summary="Status: OK")]),
                ("CMC-PU", [Result(state=State.OK, summary="Status: OK")]),
                ("CMC-Rauchmelder", [Result(state=State.OK, summary="Status: OK")]),
                ("CMC-Temperatur", [Result(state=State.OK, summary="Status: OK")]),
            ],
        ),
        (
            "cmciii_io",
            {},
            [
                (
                    "CMC-IOModul Input 1",
                    [
                        Result(state=State.OK, summary="Status: OK"),
                        Result(state=State.OK, summary="Logic: 0:OK / 1:Alarm"),
                        Result(state=State.OK, summary="Delay: 5.0 s"),
                    ],
                ),
                (
                    "CMC-IOModul Input 2",
                    [
                        Result(state=State.OK, summary="Status: OK"),
                        Result(state=State.OK, summary="Logic: 0:OK / 1:Alarm"),
                        Result(state=State.OK, summary="Delay: 5.0 s"),
                    ],
                ),
                (
                    "CMC-IOModul Input 3",
                    [
                        Result(state=State.OK, summary="Status: Off"),
                        Result(state=State.OK, summary="Logic: 0:On / 1:Off"),
                        Result(state=State.OK, summary="Delay: 5.0 s"),
                    ],
                ),
                (
                    "CMC-IOModul Input 4",
                    [
                        Result(state=State.OK, summary="Status: OK"),
                        Result(state=State.OK, summary="Logic: 0:Alarm / 1:OK"),
                        Result(state=State.OK, summary="Delay: 0.5 s"),
                    ],
                ),
                (
                    "CMC-IOModul Input 5",
                    [
                        Result(state=State.OK, summary="Status: OK"),
                        Result(state=State.OK, summary="Logic: 0:Alarm / 1:OK"),
                        Result(state=State.OK, summary="Delay: 0.5 s"),
                    ],
                ),
                (
                    "CMC-IOModul Input 6",
                    [
                        Result(state=State.OK, summary="Status: OK"),
                        Result(state=State.OK, summary="Logic: 0:Alarm / 1:OK"),
                        Result(state=State.OK, summary="Delay: 0.5 s"),
                    ],
                ),
                (
                    "CMC-IOModul Input 7",
                    [
                        Result(state=State.OK, summary="Status: Off"),
                        Result(state=State.OK, summary="Logic: 0:Off / 1:On"),
                        Result(state=State.OK, summary="Delay: 0.5 s"),
                    ],
                ),
                (
                    "CMC-IOModul Input 8",
                    [
                        Result(state=State.OK, summary="Status: Off"),
                        Result(state=State.OK, summary="Logic: 0:Off / 1:On"),
                        Result(state=State.OK, summary="Delay: 0.5 s"),
                    ],
                ),
                (
                    "CMC-IOModul Output 1",
                    [
                        Result(state=State.OK, summary="Status: OK"),
                        Result(state=State.OK, summary="Logic: 0:OK / 1:Alarm"),
                        Result(state=State.OK, summary="Relay: Off"),
                    ],
                ),
                (
                    "CMC-IOModul Output 2",
                    [
                        Result(state=State.OK, summary="Status: OK"),
                        Result(state=State.OK, summary="Logic: 0:OK / 1:Alarm"),
                        Result(state=State.OK, summary="Relay: Off"),
                    ],
                ),
                (
                    "CMC-IOModul Output 3",
                    [
                        Result(state=State.OK, summary="Status: OK"),
                        Result(state=State.OK, summary="Logic: 0:OK / 1:Alarm"),
                        Result(state=State.OK, summary="Relay: Off"),
                    ],
                ),
                (
                    "CMC-IOModul Output 4",
                    [
                        Result(state=State.OK, summary="Status: OK"),
                        Result(state=State.OK, summary="Logic: 0:OK / 1:Alarm"),
                        Result(state=State.OK, summary="Relay: Off"),
                    ],
                ),
                (
                    "CMC-PU Input 1",
                    [
                        Result(state=State.OK, summary="Status: Off"),
                        Result(state=State.OK, summary="Logic: 0:Off / 1:On"),
                        Result(state=State.OK, summary="Delay: 0.5 s"),
                    ],
                ),
                (
                    "CMC-PU Input 2",
                    [
                        Result(state=State.OK, summary="Status: Off"),
                        Result(state=State.OK, summary="Logic: 0:Off / 1:On"),
                        Result(state=State.OK, summary="Delay: 0.5 s"),
                    ],
                ),
                (
                    "CMC-PU Output",
                    [
                        Result(state=State.CRIT, summary="Status: Off"),
                        Result(state=State.OK, summary="Logic: 0:Off / 1:On"),
                        Result(state=State.OK, summary="Relay: Off"),
                    ],
                ),
            ],
        ),
        (
            "cmciii_access",
            {},
            [
                (
                    "CMC-PU Access",
                    [
                        Result(state=State.CRIT, summary="Door: Inactive"),
                        Result(state=State.OK, summary="Delay: 10 s"),
                        Result(state=State.OK, summary="Sensitivity: 0.0"),
                    ],
                )
            ],
        ),
        (
            "cmciii_temp",
            {},
            [
                (
                    "Ambient CMC-PU",
                    [
                        Metric("temp", 30.5, levels=(40.0, 45.0)),
                        Result(state=State.OK, summary="Temperature: 30.5°C"),
                        Result(
                            state=State.OK,
                            notice="Configuration: prefer user levels over device levels (used device levels)",
                        ),
                    ],
                ),
                (
                    "Ambient CMC-Temperatur",
                    [
                        Metric("temp", 27.0, levels=(35.0, 40.0)),
                        Result(state=State.OK, summary="Temperature: 27.0°C"),
                        Result(
                            state=State.OK,
                            notice="Configuration: prefer user levels over device levels (used device levels)",
                        ),
                    ],
                ),
                (
                    "Dew Point CMC-Temperatur",
                    [
                        Metric("temp", -7.8),
                        Result(state=State.OK, summary="Temperature: -7.8°C"),
                        Result(
                            state=State.OK,
                            notice="Configuration: prefer user levels over device levels (no levels found)",
                        ),
                    ],
                ),
                (
                    "System CMC-PU",
                    [
                        Result(state=State.OK, summary="[Sys Temp]"),
                        Metric("temp", 32.3, levels=(70.0, 80.0)),
                        Result(state=State.OK, summary="Temperature: 32.3°C"),
                        Result(
                            state=State.OK,
                            notice="Configuration: prefer user levels over device levels (used device levels)",
                        ),
                    ],
                ),
            ],
        ),
        (
            "cmciii_can_current",
            {},
            [
                (
                    "CMC-PU System.CAN1 Current",
                    [
                        Result(
                            state=State.OK,
                            summary="Status: OK, Current: 0.0 mA (warn/crit at 700.0/900.0 mA)",
                        ),
                        Metric("current", 0.0, levels=(0.7, 0.9)),
                    ],
                ),
                (
                    "CMC-PU System.CAN2 Current",
                    [
                        Result(
                            state=State.OK,
                            summary="Status: OK, Current: 0.0 mA (warn/crit at 700.0/900.0 mA)",
                        ),
                        Metric("current", 0.0, levels=(0.7, 0.9)),
                    ],
                ),
            ],
        ),
        (
            "cmciii_humidity",
            {"levels": (10, 12), "levels_lower": (5, 1)},
            [
                (
                    "CMC-Temperatur Humidity",
                    [
                        Result(state=State.CRIT, summary="Status: Low Warn"),
                        Result(state=State.OK, summary="9.50%"),
                        Metric("humidity", 9.5, levels=(10, 12), boundaries=(0, 100)),
                    ],
                )
            ],
        ),
    ],
)
def test_genericdataset_cmciii_check(plugin, params, items) -> None:
    for item, expected in items:
        assert run_check("cmciii", plugin, item, _generictest_cmciii(), params,) == expected, (
            "Item %s does not match" % item
        )


def _generictest_cmciii_input_regression():
    return [
        [
            ["1", "CMCIII-PU", "CMCIII-PU", "2"],
            ["2", "CMCIII-IO3", "CMCIII-IO1", "2"],
            ["3", "CMCIII-IO3", "CMCIII-IO2", "2"],
            ["4", "CMCIII-SEN", "Doors", "2"],
            ["5", "CMCIII-LEAK", "CMCIII-LEAK", "2"],
            ["6", "CMCIII-HUM", "CMCIII-back", "2"],
            ["7", "CMCIII-HUM", "CMCIII-front", "2"],
        ],
        [
            ["3.8", "Input 2.Value", "2", "", "1", "1", "1"],
            ["3.9", "Input 2.Logic", "15", "", "0", "0:Alarm / 1:OK", "3"],
            ["3.10", "Input 2.Delay", "21", "s", "-10", "0.5 s", "5"],
            ["3.11", "Input 2.Status", "7", "", "0", "OK", "4"],
            ["3.12", "Input 2.Category", "14", "", "0", "0", "0"],
            ["3.13", "Input 3.DescName", "1", "", "0", "PreUPS overvolt", "0"],
            ["3.14", "Input 3.Value", "2", "", "1", "1", "1"],
            ["3.15", "Input 3.Logic", "15", "", "0", "0:Alarm / 1:OK", "3"],
            ["3.16", "Input 3.Delay", "21", "s", "-10", "0.5 s", "5"],
            ["3.17", "Input 3.Status", "7", "", "0", "OK", "4"],
            ["3.18", "Input 3.Category", "14", "", "0", "0", "0"],
            ["3.19", "Input 4.DescName", "1", "", "0", "not connected", "0"],
            ["3.20", "Input 4.Value", "2", "", "1", "0", "0"],
            ["3.21", "Input 4.Logic", "15", "", "0", "0:Off / 1:On", "0"],
            ["3.22", "Input 4.Delay", "21", "s", "-10", "0.5 s", "5"],
            ["3.23", "Input 4.Status", "7", "", "0", "Off", "10"],
            ["3.24", "Input 4.Category", "14", "", "0", "0", "0"],
            ["3.25", "Input 5.DescName", "1", "", "0", "not connected", "0"],
            ["3.26", "Input 5.Value", "2", "", "1", "0", "0"],
            ["3.27", "Input 5.Logic", "15", "", "0", "0:Off / 1:On", "0"],
            ["3.28", "Input 5.Delay", "21", "s", "-10", "0.5 s", "5"],
            ["3.29", "Input 5.Status", "7", "", "0", "Off", "10"],
            ["3.30", "Input 5.Category", "14", "", "0", "0", "0"],
            ["3.31", "Input 6.DescName", "1", "", "0", "not connected", "0"],
            ["3.32", "Input 6.Value", "2", "", "1", "0", "0"],
            ["3.33", "Input 6.Logic", "15", "", "0", "0:Off / 1:On", "0"],
            ["3.34", "Input 6.Delay", "21", "s", "-10", "0.5 s", "5"],
            ["3.35", "Input 6.Status", "7", "", "0", "Off", "10"],
            ["3.36", "Input 6.Category", "14", "", "0", "0", "0"],
            ["3.37", "Input 7.DescName", "1", "", "0", "not connected", "0"],
            ["3.38", "Input 7.Value", "2", "", "1", "0", "0"],
            ["3.39", "Input 7.Logic", "15", "", "0", "0:Off / 1:On", "0"],
            ["3.40", "Input 7.Delay", "21", "s", "-10", "0.5 s", "5"],
            ["3.41", "Input 7.Status", "7", "", "0", "Off", "10"],
            ["3.42", "Input 7.Category", "14", "", "0", "0", "0"],
            ["3.43", "Input 8.DescName", "1", "", "0", "not connected", "0"],
            ["3.44", "Input 8.Value", "2", "", "1", "0", "0"],
            ["3.45", "Input 8.Logic", "15", "", "0", "0:Off / 1:On", "0"],
            ["3.46", "Input 8.Delay", "21", "s", "-10", "0.5 s", "5"],
            ["3.47", "Input 8.Status", "7", "", "0", "Off", "10"],
            ["3.48", "Input 8.Category", "14", "", "0", "0", "0"],
            ["4.1", "Input.DescName", "1", "", "0", "Doors", "0"],
            ["4.2", "Input.Value", "2", "", "1", "1", "1"],
            ["4.3", "Input.Delay", "21", "s", "1", "1 s", "1"],
            ["4.4", "Input.Status", "7", "", "0", "Closed", "13"],
            ["4.5", "Input.Category", "14", "", "0", "0", "0"],
        ],
    ]  # yapf: disable


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize(
    "plugin,params,expected",
    [
        (
            "cmciii",
            {},
            [
                Service(item="CMCIII-IO1", parameters={"_item_key": "CMCIII-IO1"}),
                Service(item="CMCIII-IO2", parameters={"_item_key": "CMCIII-IO2"}),
                Service(item="CMCIII-LEAK", parameters={"_item_key": "CMCIII-LEAK"}),
                Service(item="CMCIII-PU", parameters={"_item_key": "CMCIII-PU"}),
                Service(item="CMCIII-back", parameters={"_item_key": "CMCIII-back"}),
                Service(item="CMCIII-front", parameters={"_item_key": "CMCIII-front"}),
                Service(item="Doors", parameters={"_item_key": "Doors"}),
            ],
        ),
        ("cmciii_psm_current", {}, []),
        ("cmciii_psm_plugs", {}, []),
        (
            "cmciii_io",
            {},
            [
                Service(item="CMCIII-IO2 Input 2", parameters={"_item_key": "CMCIII-IO2 Input 2"}),
                Service(item="CMCIII-IO2 Input 3", parameters={"_item_key": "CMCIII-IO2 Input 3"}),
                Service(item="CMCIII-IO2 Input 4", parameters={"_item_key": "CMCIII-IO2 Input 4"}),
                Service(item="CMCIII-IO2 Input 5", parameters={"_item_key": "CMCIII-IO2 Input 5"}),
                Service(item="CMCIII-IO2 Input 6", parameters={"_item_key": "CMCIII-IO2 Input 6"}),
                Service(item="CMCIII-IO2 Input 7", parameters={"_item_key": "CMCIII-IO2 Input 7"}),
                Service(item="CMCIII-IO2 Input 8", parameters={"_item_key": "CMCIII-IO2 Input 8"}),
                Service(item="Doors Input", parameters={"_item_key": "Doors Input"}),
            ],
        ),
        ("cmciii_access", {}, []),
        ("cmciii_temp", {}, []),
        ("cmciii_temp_in_out", {}, []),
        ("cmciii_can_current", {}, []),
        ("cmciii_humidity", {}, []),
        ("cmciii_phase", {}, []),
    ],
)
def test_genericdataset_cmciii_input_regression_discovery(plugin, params, expected) -> None:
    assert (
        run_discovery(
            "cmciii",
            plugin,
            _generictest_cmciii_input_regression(),
            params,
        )
        == expected
    )


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize(
    "plugin,params,items",
    [
        (
            "cmciii",
            {},
            [
                ("CMCIII-IO1", [Result(state=State.OK, summary="Status: OK")]),
                ("CMCIII-IO2", [Result(state=State.OK, summary="Status: OK")]),
                ("CMCIII-LEAK", [Result(state=State.OK, summary="Status: OK")]),
                ("CMCIII-PU", [Result(state=State.OK, summary="Status: OK")]),
                ("CMCIII-back", [Result(state=State.OK, summary="Status: OK")]),
                ("CMCIII-front", [Result(state=State.OK, summary="Status: OK")]),
                ("Doors", [Result(state=State.OK, summary="Status: OK")]),
            ],
        ),
        (
            "cmciii_io",
            {},
            [
                (
                    "CMCIII-IO2 Input 2",
                    [
                        Result(state=State.OK, summary="Status: OK"),
                        Result(state=State.OK, summary="Logic: 0:Alarm / 1:OK"),
                        Result(state=State.OK, summary="Delay: 0.5 s"),
                    ],
                ),
                (
                    "CMCIII-IO2 Input 3",
                    [
                        Result(state=State.OK, summary="Status: OK"),
                        Result(state=State.OK, summary="Logic: 0:Alarm / 1:OK"),
                        Result(state=State.OK, summary="Delay: 0.5 s"),
                    ],
                ),
                (
                    "CMCIII-IO2 Input 4",
                    [
                        Result(state=State.OK, summary="Status: Off"),
                        Result(state=State.OK, summary="Logic: 0:Off / 1:On"),
                        Result(state=State.OK, summary="Delay: 0.5 s"),
                    ],
                ),
                (
                    "CMCIII-IO2 Input 5",
                    [
                        Result(state=State.OK, summary="Status: Off"),
                        Result(state=State.OK, summary="Logic: 0:Off / 1:On"),
                        Result(state=State.OK, summary="Delay: 0.5 s"),
                    ],
                ),
                (
                    "CMCIII-IO2 Input 6",
                    [
                        Result(state=State.OK, summary="Status: Off"),
                        Result(state=State.OK, summary="Logic: 0:Off / 1:On"),
                        Result(state=State.OK, summary="Delay: 0.5 s"),
                    ],
                ),
                (
                    "CMCIII-IO2 Input 7",
                    [
                        Result(state=State.OK, summary="Status: Off"),
                        Result(state=State.OK, summary="Logic: 0:Off / 1:On"),
                        Result(state=State.OK, summary="Delay: 0.5 s"),
                    ],
                ),
                (
                    "CMCIII-IO2 Input 8",
                    [
                        Result(state=State.OK, summary="Status: Off"),
                        Result(state=State.OK, summary="Logic: 0:Off / 1:On"),
                        Result(state=State.OK, summary="Delay: 0.5 s"),
                    ],
                ),
                (
                    "Doors Input",
                    [
                        Result(state=State.OK, summary="Status: Closed"),
                        Result(state=State.OK, summary="Delay: 1 s"),
                    ],
                ),
            ],
        ),
    ],
)
def test_genericdataset_cmciii_input_regression_check(plugin, params, items) -> None:
    for item, expected in items:
        assert (
            run_check(
                "cmciii",
                plugin,
                item,
                _generictest_cmciii_input_regression(),
                params,
            )
            == expected
        ), (
            "Item %s does not match" % item
        )
