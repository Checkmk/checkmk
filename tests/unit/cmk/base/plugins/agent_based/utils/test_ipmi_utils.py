#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.utils import ipmi


@pytest.mark.parametrize(
    'item, params, sensor, temperature_metrics_only, status_txt_mapping, exp_result', [
        (
            'something',
            {},
            ipmi.Sensor(status_txt='ok',
                        unit='',
                        value=None,
                        crit_low=None,
                        warn_low=None,
                        warn_high=None,
                        crit_high=None),
            False,
            lambda txt: State.OK,
            [
                Result(state=State.OK, summary='Status: ok'),
            ],
        ),
        (
            'PCH_1.05V',
            {},
            ipmi.Sensor(status_txt='ok',
                        unit='Volts',
                        value=1.04,
                        crit_low=0.97,
                        warn_low=None,
                        warn_high=None,
                        crit_high=1.13),
            False,
            lambda txt: State.OK,
            [
                Result(state=State.OK, summary='Status: ok'),
                Result(state=State.OK, summary='1.04 Volts'),
                Metric('PCH_1.05V', 1.04, levels=(None, 1.13)),
            ],
        ),
        (
            'PCH_1.05V',
            {},
            ipmi.Sensor(status_txt='ok',
                        unit='Volts',
                        value=1.04,
                        crit_low=0.97,
                        warn_low=None,
                        warn_high=None,
                        crit_high=1.13),
            False,
            lambda txt: State.CRIT,
            [
                Result(state=State.CRIT, summary='Status: ok'),
                Result(state=State.OK, summary='1.04 Volts'),
                Metric('PCH_1.05V', 1.04, levels=(None, 1.13)),
            ],
        ),
        (
            'PCH_1.05V',
            {},
            ipmi.Sensor(status_txt='ok',
                        unit='Volts',
                        value=1.04,
                        crit_low=0.97,
                        warn_low=None,
                        warn_high=None,
                        crit_high=1.13),
            True,
            lambda txt: State.OK,
            [
                Result(state=State.OK, summary='Status: ok'),
                Result(state=State.OK, summary='1.04 Volts'),
            ],
        ),
        (
            'Temperature',
            {},
            ipmi.Sensor(status_txt='ok',
                        unit='C',
                        value=1.04,
                        crit_low=0.97,
                        warn_low=None,
                        warn_high=None,
                        crit_high=1.13),
            True,
            lambda txt: State.OK,
            [
                Result(state=State.OK, summary='Status: ok'),
                Result(state=State.OK, summary='1.04 C'),
                Metric('value', 1.04, levels=(None, 1.13)),
            ],
        ),
        (
            'PCH_1.05V',
            {},
            ipmi.Sensor(status_txt='nc',
                        unit='Volts',
                        value=1.04,
                        crit_low=0.97,
                        warn_low=None,
                        warn_high=None,
                        crit_high=1.13),
            False,
            lambda txt: State.OK,
            [
                Result(state=State.OK, summary='Status: nc'),
                Result(state=State.OK, summary='1.04 Volts'),
                Metric('PCH_1.05V', 1.04, levels=(None, 1.13)),
                Result(state=State.WARN,
                       summary='Sensor is non-critical',
                       details='Sensor is non-critical'),
            ],
        ),
        (
            'PCH_1.05V',
            {},
            ipmi.Sensor(status_txt='ok',
                        unit='Volts',
                        value=2.1,
                        crit_low=0.97,
                        warn_low=None,
                        warn_high=None,
                        crit_high=1.13),
            False,
            lambda txt: State.OK,
            [
                Result(state=State.OK, summary='Status: ok'),
                Result(state=State.CRIT,
                       summary='2.10 Volts (warn/crit at 1.13 Volts/1.13 Volts)',
                       details='2.10 Volts (warn/crit at 1.13 Volts/1.13 Volts)'),
                Metric('PCH_1.05V', 2.1, levels=(None, 1.13)),
            ],
        ),
        (
            'PCH_1.05V',
            {},
            ipmi.Sensor(status_txt='ok',
                        unit='Volts',
                        value=0.5,
                        crit_low=0.97,
                        warn_low=None,
                        warn_high=None,
                        crit_high=1.13),
            False,
            lambda txt: State.OK,
            [
                Result(state=State.OK, summary='Status: ok'),
                Result(state=State.CRIT,
                       summary='0.50 Volts (warn/crit below 0.97 Volts/0.97 Volts)',
                       details='0.50 Volts (warn/crit below 0.97 Volts/0.97 Volts)'),
                Metric('PCH_1.05V', 0.5, levels=(None, 1.13)),
            ],
        ),
        (
            'PCH_1.05V',
            ({
                'numerical_sensor_levels': [('PCH_1.05V', {
                    'lower': (1.0, 2.0),
                    'upper': (1.0, 4.0),
                })]
            }),
            ipmi.Sensor(status_txt='ok',
                        unit='Volts',
                        value=1.04,
                        crit_low=0.97,
                        warn_low=None,
                        warn_high=None,
                        crit_high=1.13),
            False,
            lambda txt: State.OK,
            [
                Result(state=State.OK, summary='Status: ok'),
                Result(state=State.OK, summary='1.04 Volts'),
                Metric('PCH_1.05V', 1.04, levels=(None, 1.13)),
                Result(state=State.CRIT,
                       summary='PCH_1.05V: 1.04 Volts (warn/crit below 1.00 Volts/2.00 Volts)',
                       details='PCH_1.05V: 1.04 Volts (warn/crit below 1.00 Volts/2.00 Volts)')
            ],
        ),
        (
            'PCH_1.05V',
            ({
                'numerical_sensor_levels': [('PCH_1.05V', {
                    'upper': (1.0, 4.0),
                })]
            }),
            ipmi.Sensor(status_txt='ok',
                        unit='Volts',
                        value=1.04,
                        crit_low=0.97,
                        warn_low=None,
                        warn_high=None,
                        crit_high=1.13),
            False,
            lambda txt: State.OK,
            [
                Result(state=State.OK, summary='Status: ok'),
                Result(state=State.OK, summary='1.04 Volts'),
                Metric('PCH_1.05V', 1.04, levels=(None, 1.13)),
                Result(state=State.WARN,
                       summary='PCH_1.05V: 1.04 Volts (warn/crit at 1.00 Volts/4.00 Volts)',
                       details='PCH_1.05V: 1.04 Volts (warn/crit at 1.00 Volts/4.00 Volts)')
            ],
        ),
        (
            'PCH_1.05V',
            ({
                'sensor_states': [('ok', 3)]
            }),
            ipmi.Sensor(status_txt='ok',
                        unit='Volts',
                        value=1.04,
                        crit_low=0.97,
                        warn_low=None,
                        warn_high=None,
                        crit_high=1.13),
            False,
            lambda txt: State.OK,
            [
                Result(state=State.OK, summary='Status: ok'),
                Result(state=State.OK, summary='1.04 Volts'),
                Metric('PCH_1.05V', 1.04, levels=(None, 1.13)),
                Result(state=State.UNKNOWN,
                       summary='User-defined state',
                       details='User-defined state'),
            ],
        ),
    ])
def test_check_ipmi_detailed(
    item,
    params,
    sensor,
    temperature_metrics_only,
    status_txt_mapping,
    exp_result,
):
    assert list(
        ipmi.check_ipmi_detailed(
            item,
            params,
            sensor,
            temperature_metrics_only,
            status_txt_mapping,
        )) == exp_result


SECTION = {
    'Ambient': ipmi.Sensor(status_txt='ok',
                           unit='degrees_C',
                           value=18.5,
                           crit_low=1.0,
                           warn_low=6.0,
                           warn_high=37.0,
                           crit_high=42.0),
    'CPU': ipmi.Sensor(status_txt='ok',
                       unit='degrees_C',
                       value=33.0,
                       crit_low=None,
                       warn_low=None,
                       warn_high=95.0,
                       crit_high=99.0),
    'I2C4_error_ratio': ipmi.Sensor(status_txt='ok',
                                    unit='percent',
                                    value=0.0,
                                    crit_low=None,
                                    warn_low=None,
                                    warn_high=10.0,
                                    crit_high=20.0),
    'PCH_1.05V': ipmi.Sensor(status_txt='ok',
                             unit='Volts',
                             value=1.04,
                             crit_low=0.97,
                             warn_low=None,
                             warn_high=None,
                             crit_high=1.13),
    'Total_Power': ipmi.Sensor(status_txt='ok',
                               unit='Watts',
                               value=48.0,
                               crit_low=None,
                               warn_low=None,
                               warn_high=None,
                               crit_high=498.0),
    'CMOS_Battery': ipmi.Sensor(status_txt='ok',
                                unit='',
                                value=None,
                                crit_low=None,
                                warn_low=None,
                                warn_high=None,
                                crit_high=None),
    'MSR_Info_Log': ipmi.Sensor(status_txt='ns (No Reading)',
                                unit='',
                                value=None,
                                crit_low=None,
                                warn_low=None,
                                warn_high=None,
                                crit_high=None),
    'PS1_Status': ipmi.Sensor(
        status_txt='ok (Presence detected, Failure detected     <= NOT OK !!)',
        unit='',
        value=None,
        crit_low=None,
        warn_low=None,
        warn_high=None,
        crit_high=None),
    'Power_Redundancy': ipmi.Sensor(status_txt='ok (Fully Redundant)',
                                    unit='',
                                    value=None,
                                    crit_low=None,
                                    warn_low=None,
                                    warn_high=None,
                                    crit_high=None),
    'VCORE': ipmi.Sensor(status_txt='ok (State Deasserted)',
                         unit='',
                         value=None,
                         crit_low=None,
                         warn_low=None,
                         warn_high=None,
                         crit_high=None),
}


@pytest.mark.parametrize('params, status_txt_mapping, exp_result', [
    (
        {},
        lambda txt: State.OK,
        [
            Metric('ambient_temp', 18.5),
            Result(state=State.OK, summary='10 sensors OK'),
        ],
    ),
    (
        {},
        lambda txt: ('Failure detected' in txt and State.CRIT) or
        ('State Deasserted' in txt and State.WARN or State.OK),
        [
            Metric('ambient_temp', 18.5),
            Result(
                state=State.CRIT,
                summary=
                '10 sensors - 8 OK - 1 WARN: VCORE (ok (State Deasserted)) - 1 CRIT: PS1_Status (ok (Presence detected, Failure detected     <= NOT OK !!))',
                details=
                '10 sensors - 8 OK - 1 WARN: VCORE (ok (State Deasserted)) - 1 CRIT: PS1_Status (ok (Presence detected, Failure detected     <= NOT OK !!))'
            )
        ],
    ),
    (
        ({
            "ignored_sensors": ["CPU", "VCORE"]
        }),
        lambda txt: State.OK,
        [
            Metric('ambient_temp', 18.5),
            Result(state=State.OK,
                   summary='10 sensors - 8 OK - 2 skipped',
                   details='10 sensors - 8 OK - 2 skipped'),
        ],
    ),
    (
        ({
            "ignored_sensorstates": ["ns", "nr", "na"]
        }),
        lambda txt: State.OK,
        [
            Metric('ambient_temp', 18.5),
            Result(state=State.OK,
                   summary='10 sensors - 9 OK - 1 skipped',
                   details='10 sensors - 9 OK - 1 skipped'),
        ],
    ),
    (
        ({
            "ignored_sensorstates": ["ns", "nr", "na"],
            'sensor_states': [('ok', 1)],
        }),
        lambda txt: State.OK,
        [
            Metric('ambient_temp', 18.5),
            Result(
                state=State.WARN,
                summary=
                '10 sensors - 9 WARN: Ambient (ok), CPU (ok), I2C4_error_ratio (ok), PCH_1.05V (ok), Total_Power (ok), CMOS_Battery (ok), PS1_Status (ok (Presence detected, Failure detected     <= NOT OK !!)), Power_Redundancy (ok (Fully Redundant)), VCORE (ok (State Deasserted)) - 1 skipped',
                details=
                '10 sensors - 9 WARN: Ambient (ok), CPU (ok), I2C4_error_ratio (ok), PCH_1.05V (ok), Total_Power (ok), CMOS_Battery (ok), PS1_Status (ok (Presence detected, Failure detected     <= NOT OK !!)), Power_Redundancy (ok (Fully Redundant)), VCORE (ok (State Deasserted)) - 1 skipped'
            ),
        ],
    ),
    (
        ({
            'numerical_sensor_levels': [('PCH_1.05V', {
                'upper': (1.0, 4.0),
            })]
        }),
        lambda txt: State.OK,
        [
            Metric('ambient_temp', 18.5),
            Result(
                state=State.WARN,
                summary=
                '10 sensors - 9 OK - 1 WARN: PCH_1.05V: 1.04 Volts (warn/crit at 1.00 Volts/4.00 Volts)',
                details=
                '10 sensors - 9 OK - 1 WARN: PCH_1.05V: 1.04 Volts (warn/crit at 1.00 Volts/4.00 Volts)'
            )
        ],
    ),
])
def test_check_ipmi_summarized(params, status_txt_mapping, exp_result):
    assert list(ipmi.check_ipmi_summarized(
        params,
        SECTION,
        status_txt_mapping,
    )) == exp_result
