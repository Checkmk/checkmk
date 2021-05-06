#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from testlib import Check  # type: ignore[import]

from cmk.utils.type_defs import CheckPluginName, SectionName
import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State


@pytest.fixture(name="discovery_params")
def mock_discovery_params(monkeypatch):
    cmciii = Check('cmciii')
    discovery_params = cmciii.context['discovery_params']
    cmciii.context['discovery_params'] = lambda: {'use_sensor_descriptions': False}
    yield
    cmciii.context['discovery_params'] = discovery_params


def run_discovery(section, plugin, info):
    section_plugin = agent_based_register.get_section_plugin(SectionName(section))
    assert section_plugin
    plugin = agent_based_register.get_check_plugin(CheckPluginName(plugin))
    assert plugin
    return sorted(plugin.discovery_function(section_plugin.parse_function(info)))


def run_check(section, plugin, item, info):
    section_plugin = agent_based_register.get_section_plugin(SectionName(section))
    assert section_plugin
    plugin = agent_based_register.get_check_plugin(CheckPluginName(plugin))
    assert plugin
    return list(
        plugin.check_function(item=item, params={}, section=section_plugin.parse_function(info)))


def _leakage_info(status, position):
    return [
        [['4', 'CMCIII-LEAK', 'CMCIII-LEAK', '2']],
        [
            ['4.1', 'Leakage.DescName', '1', '', '0', 'Leakage', '0'],
            ['4.2', 'Leakage.Position', '33', '', '0', position, '0'],
            ['4.3', 'Leakage.Delay', '21', 's', '1', '1 s', '1'],
            ['4.4', 'Leakage.Status', '7', '', '0', status, '4'],
            ['4.5', 'Leakage.Category', '14', '', '0', '0', '0'],
        ],
    ]


@pytest.mark.usefixtures("load_all_agent_based_plugins")
@pytest.mark.parametrize('status, position, expected', [
    (
        'OK',
        'None',
        [
            Result(state=State.OK, summary='Status: OK'),
            Result(state=State.OK, summary='Delay: 1 s'),
        ],
    ),
    (
        'ProbeOpen',
        'None',
        [
            Result(state=State.CRIT, summary='Status: ProbeOpen'),
            Result(state=State.OK, summary='Delay: 1 s'),
        ],
    ),
    (
        'Alarm',
        'Zone 1',
        [
            Result(state=State.CRIT, summary='Status: Alarm'),
            Result(state=State.OK, summary='Delay: 1 s'),
        ],
    ),
])
def test_cmciii_leakage_sensors(discovery_params, status, position, expected):
    assert run_check('cmciii', 'cmciii_leakage', "CMCIII-LEAK Leakage",
                     _leakage_info(status, position)) == expected


def _lcp_sensor():
    return [
        [['2', 'LCP-I Flush 30kW', 'Liquid Cooling Package', '2']],
        [
            ['2.1', 'Air.Device.DescName', '1', '', '0', 'Fan Unit', '0'],
            ['2.2', 'Air.Device.Software Revision', '91', '', '0', 'V09.005', '0'],
            ['2.3', 'Air.Device.Hardware Revision', '91', '', '0', 'V0000', '0'],
            ['2.4', 'Air.Device.Status', '7', '', '0', 'OK', '4'],
            ['2.5', 'Air.Device.Category', '14', '', '0', '2', '2'],
            ['2.6', 'Air.Temperature.DescName', '1', '', '0', 'Air-Temperatures', '0'],
            ['2.7', 'Air.Temperature.In-Top', '2', '°C', '-10', '19.8 °C', '198'],
            ['2.8', 'Air.Temperature.In-Mid', '2', '°C', '-10', '19.0 °C', '190'],
            ['2.9', 'Air.Temperature.In-Bot', '2', '°C', '-10', '18.2 °C', '182'],
            ['2.10', 'Air.Temperature.Out-Top', '2', '°C', '-10', '19.9 °C', '199'],
            ['2.11', 'Air.Temperature.Out-Mid', '2', '°C', '-10', '18.9 °C', '189'],
            ['2.12', 'Air.Temperature.Out-Bot', '2', '°C', '-10', '18.0 °C', '180'],
            ['2.13', 'Air.Temperature.Status', '7', '', '0', 'OK', '4'],
            ['2.14', 'Air.Temperature.Category', '14', '', '0', '2', '2'],
            ['2.15', 'Air.Server-In.DescName', '1', '', '0', 'Server-In', '0'],
            ['2.16', 'Air.Server-In.Setpoint', '17', '°C', '-10', '23.0 °C', '230'],
            ['2.17', 'Air.Server-In.Average', '2', '°C', '-10', '19.0 °C', '190'],
            ['2.18', 'Air.Server-In.SetPtHighAlarm', '3', '°C', '-10', '35.0 °C', '350'],
            ['2.19', 'Air.Server-In.SetPtHighWarning', '4', '°C', '-10', '30.0 °C', '300'],
            ['2.20', 'Air.Server-In.SetPtLowWarning', '9', '°C', '-10', '15.0 °C', '150'],
            ['2.21', 'Air.Server-In.SetPtLowAlarm', '5', '°C', '-10', '10.0 °C', '100'],
            ['2.22', 'Air.Server-In.Hysteresis', '6', '%', '1', '5 %', '5'],
            ['2.23', 'Air.Server-In.Status', '7', '', '0', 'OK', '4'],
            ['2.24', 'Air.Server-In.Category', '14', '', '0', '2', '2'],
            ['2.25', 'Air.Server-Out.DescName', '1', '', '0', 'Server-Out', '0'],
            ['2.26', 'Air.Server-Out.Average', '2', '°C', '-10', '18.9 °C', '189'],
            ['2.27', 'Air.Server-Out.SetPtHighAlarm', '3', '°C', '-10', '35.0 °C', '350'],
            ['2.28', 'Air.Server-Out.SetPtHighWarning', '4', '°C', '-10', '30.0 °C', '300'],
            ['2.29', 'Air.Server-Out.SetPtLowWarning', '9', '°C', '-10', '15.0 °C', '150'],
            ['2.30', 'Air.Server-Out.SetPtLowAlarm', '5', '°C', '-10', '10.0 °C', '100'],
            ['2.31', 'Air.Server-Out.Hysteresis', '6', '%', '1', '5 %', '5'],
            ['2.32', 'Air.Server-Out.Status', '7', '', '0', 'OK', '4'],
            ['2.33', 'Air.Server-Out.Category', '14', '', '0', '2', '2'],
            ['2.34', 'Air.Fans.All-Fans.SetPtLowWarning', '4', '%', '1', '14 %', '14'],
            ['2.35', 'Air.Fans.Fan1.DescName', '1', '', '0', 'Fan1', '0'],
            ['2.36', 'Air.Fans.Fan1.Rpm', '2', '%', '1', '19 %', '19'],
            ['2.37', 'Air.Fans.Fan1.Status', '7', '', '0', 'OK', '4'],
            ['2.38', 'Air.Fans.Fan1.Category', '14', '', '0', '2', '2'],
            ['2.39', 'Air.Fans.Fan2.DescName', '1', '', '0', 'Fan2', '0'],
            ['2.40', 'Air.Fans.Fan2.Rpm', '2', '%', '1', '19 %', '19'],
            ['2.41', 'Air.Fans.Fan2.Status', '7', '', '0', 'OK', '4'],
            ['2.42', 'Air.Fans.Fan2.Category', '14', '', '0', '2', '2'],
            ['2.43', 'Air.Fans.Fan3.DescName', '1', '', '0', 'Fan3', '0'],
            ['2.44', 'Air.Fans.Fan3.Rpm', '2', '%', '1', '19 %', '19'],
            ['2.45', 'Air.Fans.Fan3.Status', '7', '', '0', 'OK', '4'],
            ['2.46', 'Air.Fans.Fan3.Category', '14', '', '0', '2', '2'],
            ['2.47', 'Air.Fans.Fan4.DescName', '1', '', '0', 'Fan4', '0'],
            ['2.48', 'Air.Fans.Fan4.Rpm', '2', '%', '1', '19 %', '19'],
            ['2.49', 'Air.Fans.Fan4.Status', '7', '', '0', 'OK', '4'],
            ['2.50', 'Air.Fans.Fan4.Category', '14', '', '0', '2', '2'],
        ],
    ]


@pytest.mark.parametrize('plugin, expected', [
    (
        'cmciii_temp_in_out',
        [
            Service(item='Air LCP In Bottom', parameters={'_item_key': 'Air LCP In Bottom'}),
            Service(item='Air LCP In Middle', parameters={'_item_key': 'Air LCP In Middle'}),
            Service(item='Air LCP In Top', parameters={'_item_key': 'Air LCP In Top'}),
            Service(item='Air LCP Out Bottom', parameters={'_item_key': 'Air LCP Out Bottom'}),
            Service(item='Air LCP Out Middle', parameters={'_item_key': 'Air LCP Out Middle'}),
            Service(item='Air LCP Out Top', parameters={'_item_key': 'Air LCP Out Top'}),
        ],
    ),
    (
        'cmciii_temp',
        [],
    ),
])
def test_cmciii_lcp_discovery(discovery_params, plugin, expected):
    assert run_discovery('cmciii', plugin, _lcp_sensor()) == expected


@pytest.mark.parametrize('item, expected', [
    (
        'Air LCP In Bottom',
        [
            Result(state=State.OK, summary='18.2 °C'),
            Metric('temp', 18.2),
        ],
    ),
    (
        'Air LCP In Middle',
        [
            Result(state=State.OK, summary='19.0 °C'),
            Metric('temp', 19.0),
        ],
    ),
    (
        'Air LCP In Top',
        [
            Result(state=State.OK, summary='19.8 °C'),
            Metric('temp', 19.8),
        ],
    ),
])
def test_cmciii_lcp_check(discovery_params, item, expected):
    assert run_check('cmciii', 'cmciii_temp_in_out', item, _lcp_sensor()) == expected


def _phase_sensor():
    return [
        [['1', 'PDU-MET', 'Master PDU', '2']],
        [
            ['1.1', 'Unit.Frequency.Value', '2', 'Hz', '-10', '50.0 Hz', '500'],
            ['1.2', 'Unit.Neutral Current.DescName', '1', '', '0', 'Neutral Current', '0'],
            ['1.3', 'Unit.Neutral Current.Value', '2', 'A', '-100', '3.05 A', '305'],
            ['1.4', 'Unit.Neutral Current.SetPtHighAlarm', '3', 'A', '-100', '0.00 A', '0'],
            ['1.5', 'Unit.Neutral Current.SetPtHighWarning', '4', 'A', '-100', '0.00 A', '0'],
            ['1.6', 'Unit.Neutral Current.SetPtLowWarning', '9', 'A', '-100', '0.00 A', '0'],
            ['1.7', 'Unit.Neutral Current.SetPtLowAlarm', '5', 'A', '-100', '0.00 A', '0'],
            ['1.8', 'Unit.Neutral Current.Hysteresis', '6', '%', '-10', '1.0 %', '10'],
            ['1.9', 'Unit.Neutral Current.Status', '7', '', '0', 'OK', '4'],
            ['1.10', 'Unit.Neutral Current.Category', '14', '', '0', '4', '4'],
            ['1.11', 'Unit.Power.Active.DescName', '1', '', '0', 'Power Active', '0'],
            ['1.12', 'Unit.Power.Active.Value', '2', 'W', '1', '1637 W', '1639'],
            ['1.13', 'Unit.Power.Active.SetPtHighAlarm', '3', 'W', '1', '0 W', '0'],
            ['1.14', 'Unit.Power.Active.SetPtHighWarning', '4', 'W', '1', '0 W', '0'],
            ['1.15', 'Unit.Power.Active.SetPtLowWarning', '9', 'W', '1', '0 W', '0'],
            ['1.16', 'Unit.Power.Active.SetPtLowAlarm', '5', 'W', '1', '0 W', '0'],
            ['1.17', 'Unit.Power.Active.Hysteresis', '6', '%', '-10', '1.0 %', '10'],
            ['1.18', 'Unit.Power.Active.Status', '7', '', '0', 'OK', '4'],
            ['1.19', 'Unit.Power.Active.Category', '14', '', '0', '4', '4'],
            ['1.20', 'Unit.Energy.Active.Value', '2', 'kWh', '-10', '7636.5 kWh', '76365'],
            ['1.21', 'Unit.Energy.Active.Runtime.Value', '2', 's', '1', '18457906 s', '18457907'],
            ['1.22', 'Unit.Energy.Active Custom.Value', '2', 'kWh', '-10', '7636.5 kWh', '76365'],
            [
                '1.23', 'Unit.Energy.Active Custom.Runtime.Value', '2', 's', '1', '18457906 s',
                '18457907'
            ],
            ['1.24', 'Unit.Mounting Position', '93', '', '0', 'Vertical up', '1'],
            ['1.25', 'Phase L1.Voltage.DescName', '1', '', '0', 'L1 Voltage', '0'],
            ['1.26', 'Phase L1.Voltage.Value', '2', 'V', '-10', '229.8 V', '2299'],
            ['1.27', 'Phase L1.Voltage.SetPtHighAlarm', '3', 'V', '-10', '260.0 V', '2600'],
            ['1.28', 'Phase L1.Voltage.SetPtHighWarning', '4', 'V', '-10', '260.0 V', '2600'],
            ['1.29', 'Phase L1.Voltage.SetPtLowWarning', '9', 'V', '-10', '0.0 V', '0'],
            ['1.30', 'Phase L1.Voltage.SetPtLowAlarm', '5', 'V', '-10', '0.0 V', '0'],
            ['1.31', 'Phase L1.Voltage.Hysteresis', '6', '%', '-10', '1.0 %', '10'],
            ['1.32', 'Phase L1.Voltage.Status', '7', '', '0', 'OK', '4'],
            ['1.33', 'Phase L1.Voltage.Category', '14', '', '0', '4', '4'],
            ['1.34', 'Phase L1.Current.DescName', '1', '', '0', 'L1 Current', '0'],
            ['1.35', 'Phase L1.Current.Value', '2', 'A', '-100', '4.44 A', '445'],
            ['1.36', 'Phase L1.Current.SetPtHighAlarm', '3', 'A', '-100', '0.00 A', '0'],
            ['1.37', 'Phase L1.Current.SetPtHighWarning', '4', 'A', '-100', '0.00 A', '0'],
            ['1.38', 'Phase L1.Current.SetPtLowWarning', '9', 'A', '-100', '0.00 A', '0'],
            ['1.39', 'Phase L1.Current.SetPtLowAlarm', '5', 'A', '-100', '0.00 A', '0'],
            ['1.40', 'Phase L1.Current.Hysteresis', '6', '%', '-10', '1.0 %', '10'],
            ['1.41', 'Phase L1.Current.Status', '7', '', '0', 'OK', '4'],
            ['1.42', 'Phase L1.Current.Category', '14', '', '0', '4', '4'],
            ['1.43', 'Phase L1.Power.Factor.Value', '2', '', '-100', '1.00', '100'],
            ['1.44', 'Phase L1.Power.Active.DescName', '1', '', '0', 'L1 Power', '0'],
            ['1.45', 'Phase L1.Power.Active.Value', '2', 'W', '1', '1020 W', '1023'],
            ['1.46', 'Phase L1.Power.Active.SetPtHighAlarm', '3', 'W', '1', '0 W', '0'],
            ['1.47', 'Phase L1.Power.Active.SetPtHighWarning', '4', 'W', '1', '0 W', '0'],
            ['1.48', 'Phase L1.Power.Active.SetPtLowWarning', '9', 'W', '1', '0 W', '0'],
            ['1.49', 'Phase L1.Power.Active.SetPtLowAlarm', '5', 'W', '1', '0 W', '0'],
            ['1.50', 'Phase L1.Power.Active.Hysteresis', '6', '%', '-10', '1.0 %', '10'],
            ['1.51', 'Phase L1.Power.Active.Status', '7', '', '0', 'OK', '4'],
            ['1.52', 'Phase L1.Power.Active.Category', '14', '', '0', '4', '4'],
            ['1.53', 'Phase L1.Power.Reactive.Value', '2', 'var', '1', '11 var', '10'],
            ['1.54', 'Phase L1.Power.Apparent.Value', '2', 'VA', '1', '1020 VA', '1023'],
            ['1.55', 'Phase L1.Energy.Active.Value', '2', 'kWh', '-10', '4772.2 kWh', '47722'],
            [
                '1.56', 'Phase L1.Energy.Active Custom.Value', '2', 'kWh', '-10', '4772.2 kWh',
                '47722'
            ],
            ['1.57', 'Phase L1.Energy.Apparent.Value', '2', 'kVAh', '-10', '4871.2 kVAh', '48712'],
            ['1.58', 'Phase L2.Voltage.DescName', '1', '', '0', 'L2 Voltage', '0'],
            ['1.59', 'Phase L2.Voltage.Value', '2', 'V', '-10', '230.2 V', '2302'],
            ['1.60', 'Phase L2.Voltage.SetPtHighAlarm', '3', 'V', '-10', '260.0 V', '2600'],
            ['1.61', 'Phase L2.Voltage.SetPtHighWarning', '4', 'V', '-10', '260.0 V', '2600'],
            ['1.62', 'Phase L2.Voltage.SetPtLowWarning', '9', 'V', '-10', '0.0 V', '0'],
            ['1.63', 'Phase L2.Voltage.SetPtLowAlarm', '5', 'V', '-10', '0.0 V', '0'],
            ['1.64', 'Phase L2.Voltage.Hysteresis', '6', '%', '-10', '1.0 %', '10'],
            ['1.65', 'Phase L2.Voltage.Status', '7', '', '0', 'OK', '4'],
            ['1.66', 'Phase L2.Voltage.Category', '14', '', '0', '4', '4'],
            ['1.67', 'Phase L2.Current.DescName', '1', '', '0', 'L2 Current', '0'],
            ['1.68', 'Phase L2.Current.Value', '2', 'A', '-100', '1.54 A', '154'],
            ['1.69', 'Phase L2.Current.SetPtHighAlarm', '3', 'A', '-100', '0.00 A', '0'],
            ['1.70', 'Phase L2.Current.SetPtHighWarning', '4', 'A', '-100', '0.00 A', '0'],
            ['1.71', 'Phase L2.Current.SetPtLowWarning', '9', 'A', '-100', '0.00 A', '0'],
            ['1.72', 'Phase L2.Current.SetPtLowAlarm', '5', 'A', '-100', '0.00 A', '0'],
            ['1.73', 'Phase L2.Current.Hysteresis', '6', '%', '-10', '1.0 %', '10'],
            ['1.74', 'Phase L2.Current.Status', '7', '', '0', 'OK', '4'],
            ['1.75', 'Phase L2.Current.Category', '14', '', '0', '4', '4'],
            ['1.76', 'Phase L2.Power.Factor.Value', '2', '', '-100', '0.87', '88'],
            ['1.77', 'Phase L2.Power.Active.DescName', '1', '', '0', 'L2 Power', '0'],
            ['1.78', 'Phase L2.Power.Active.Value', '2', 'W', '1', '310 W', '311'],
            ['1.79', 'Phase L2.Power.Active.SetPtHighAlarm', '3', 'W', '1', '0 W', '0'],
            ['1.80', 'Phase L2.Power.Active.SetPtHighWarning', '4', 'W', '1', '0 W', '0'],
            ['1.81', 'Phase L2.Power.Active.SetPtLowWarning', '9', 'W', '1', '0 W', '0'],
            ['1.82', 'Phase L2.Power.Active.SetPtLowAlarm', '5', 'W', '1', '0 W', '0'],
            ['1.83', 'Phase L2.Power.Active.Hysteresis', '6', '%', '-10', '1.0 %', '10'],
            ['1.84', 'Phase L2.Power.Active.Status', '7', '', '0', 'OK', '4'],
            ['1.85', 'Phase L2.Power.Active.Category', '14', '', '0', '4', '4'],
            ['1.86', 'Phase L2.Power.Reactive.Value', '2', 'var', '1', '174 var', '172'],
            ['1.87', 'Phase L2.Power.Apparent.Value', '2', 'VA', '1', '355 VA', '355'],
            ['1.88', 'Phase L2.Energy.Active.Value', '2', 'kWh', '-10', '1378.6 kWh', '13786'],
            [
                '1.89', 'Phase L2.Energy.Active Custom.Value', '2', 'kWh', '-10', '1378.6 kWh',
                '13786'
            ],
            ['1.90', 'Phase L2.Energy.Apparent.Value', '2', 'kVAh', '-10', '1541.5 kVAh', '15415'],
            ['1.91', 'Phase L3.Voltage.DescName', '1', '', '0', 'L3 Voltage', '0'],
            ['1.92', 'Phase L3.Voltage.Value', '2', 'V', '-10', '230.2 V', '2302'],
            ['1.93', 'Phase L3.Voltage.SetPtHighAlarm', '3', 'V', '-10', '260.0 V', '2600'],
            ['1.94', 'Phase L3.Voltage.SetPtHighWarning', '4', 'V', '-10', '260.0 V', '2600'],
            ['1.95', 'Phase L3.Voltage.SetPtLowWarning', '9', 'V', '-10', '0.0 V', '0'],
            ['1.96', 'Phase L3.Voltage.SetPtLowAlarm', '5', 'V', '-10', '0.0 V', '0'],
            ['1.97', 'Phase L3.Voltage.Hysteresis', '6', '%', '-10', '1.0 %', '10'],
            ['1.98', 'Phase L3.Voltage.Status', '7', '', '0', 'OK', '4'],
            ['1.99', 'Phase L3.Voltage.Category', '14', '', '0', '4', '4'],
            ['1.100', 'Phase L3.Current.DescName', '1', '', '0', 'L3 Current', '0'],
            ['1.101', 'Phase L3.Current.Value', '2', 'A', '-100', '1.62 A', '161'],
            ['1.102', 'Phase L3.Current.SetPtHighAlarm', '3', 'A', '-100', '0.00 A', '0'],
            ['1.103', 'Phase L3.Current.SetPtHighWarning', '4', 'A', '-100', '0.00 A', '0'],
            ['1.104', 'Phase L3.Current.SetPtLowWarning', '9', 'A', '-100', '0.00 A', '0'],
            ['1.105', 'Phase L3.Current.SetPtLowAlarm', '5', 'A', '-100', '0.00 A', '0'],
            ['1.106', 'Phase L3.Current.Hysteresis', '6', '%', '-10', '1.0 %', '10'],
            ['1.107', 'Phase L3.Current.Status', '7', '', '0', 'OK', '4'],
            ['1.108', 'Phase L3.Current.Category', '14', '', '0', '4', '4'],
            ['1.109', 'Phase L3.Power.Factor.Value', '2', '', '-100', '0.82', '82'],
            ['1.110', 'Phase L3.Power.Active.DescName', '1', '', '0', 'L3 Power', '0'],
            ['1.111', 'Phase L3.Power.Active.Value', '2', 'W', '1', '305 W', '305'],
            ['1.112', 'Phase L3.Power.Active.SetPtHighAlarm', '3', 'W', '1', '0 W', '0'],
            ['1.113', 'Phase L3.Power.Active.SetPtHighWarning', '4', 'W', '1', '0 W', '0'],
            ['1.114', 'Phase L3.Power.Active.SetPtLowWarning', '9', 'W', '1', '0 W', '0'],
            ['1.115', 'Phase L3.Power.Active.SetPtLowAlarm', '5', 'W', '1', '0 W', '0'],
            ['1.116', 'Phase L3.Power.Active.Hysteresis', '6', '%', '-10', '1.0 %', '10'],
            ['1.117', 'Phase L3.Power.Active.Status', '7', '', '0', 'OK', '4'],
            ['1.118', 'Phase L3.Power.Active.Category', '14', '', '0', '4', '4'],
            ['1.119', 'Phase L3.Power.Reactive.Value', '2', 'var', '1', '211 var', '211'],
            ['1.120', 'Phase L3.Power.Apparent.Value', '2', 'VA', '1', '371 VA', '371'],
            ['1.121', 'Phase L3.Energy.Active.Value', '2', 'kWh', '-10', '1485.7 kWh', '14857'],
            [
                '1.122', 'Phase L3.Energy.Active Custom.Value', '2', 'kWh', '-10', '1485.7 kWh',
                '14857'
            ],
            ['1.123', 'Phase L3.Energy.Apparent.Value', '2', 'kVAh', '-10', '1816.4 kVAh', '18164'],
            ['1.124', 'Memory.USB-Stick.DescName', '1', '', '0', 'USB-Stick', '0'],
            ['1.125', 'Memory.USB-Stick.Size', '2', 'GB', '-10', '0.0 GB', '0'],
            ['1.126', 'Memory.USB-Stick.Usage', '2', '%', '1', '0 %', '0'],
            ['1.127', 'Memory.USB-Stick.Command', '81', '', '0', '--', '4'],
            ['1.128', 'Memory.USB-Stick.Status', '7', '', '0', 'n.a.', '1'],
            ['1.129', 'Memory.USB-Stick.Category', '14', '', '1', '16', '16'],
        ]
    ]


def test_phase_sensors(discovery_params):
    assert run_discovery('cmciii', 'cmciii_phase', _phase_sensor()) == [
        Service(item='Master_PDU Phase 1', parameters={'_item_key': 'Master_PDU Phase 1'}),
        Service(item='Master_PDU Phase 2', parameters={'_item_key': 'Master_PDU Phase 2'}),
        Service(item='Master_PDU Phase 3', parameters={'_item_key': 'Master_PDU Phase 3'}),
    ]


@pytest.mark.parametrize('item, expected', [
    (
        'Master_PDU Phase 1',
        [
            Result(state=State.OK, summary='Voltage: 229.9 V'),
            Metric('voltage', 229.9),
            Result(state=State.OK, summary='Current: 4.5 A'),
            Metric('current', 4.45),
            Result(state=State.OK, summary='Power: 1023.0 W'),
            Metric('power', 1023.0),
            Result(state=State.OK, summary='Apparent Power: 1023.0 VA'),
            Metric('appower', 1023.0),
            Result(state=State.OK, summary='Energy: 4772.2 Wh'),
            Metric('energy', 4772.2),
        ],
    ),
])
def test_cmciii_phase_check(discovery_params, item, expected):
    assert run_check('cmciii', 'cmciii_phase', item, _phase_sensor()) == expected
