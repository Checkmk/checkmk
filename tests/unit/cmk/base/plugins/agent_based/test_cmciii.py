#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.utils.type_defs import CheckPluginName, SectionName
import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State


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
def test_cmciii_leakage_sensors(status, position, expected):
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
            Service(item='Air LCP In Bottom'),
            Service(item='Air LCP In Middle'),
            Service(item='Air LCP In Top'),
            Service(item='Air LCP Out Bottom'),
            Service(item='Air LCP Out Middle'),
            Service(item='Air LCP Out Top'),
        ],
    ),
    (
        'cmciii_temp',
        [],
    ),
])
def test_cmciii_lcp_discovery(plugin, expected):
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
def test_cmciii_lcp_check(item, expected):
    assert run_check('cmciii', 'cmciii_temp_in_out', item, _lcp_sensor()) == expected
