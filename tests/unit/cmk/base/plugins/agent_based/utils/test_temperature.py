#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import freezegun  # type: ignore[import]
import pytest  # type: ignore[import]

from cmk.base.plugins.agent_based.utils import temperature
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    Result,
    Metric,
    State as state,
    IgnoreResultsError,
)


def test_check_trend_raises():

    with pytest.raises(IgnoreResultsError):
        _ = list(
            temperature._check_trend(
                {},  # uninitialized -> raise
                23.,
                {"period": 2},
                "c",
                0.,
                0.,
                "my_test",
            ))


def test_check_trend_simple():

    with freezegun.freeze_time('1970-01-01 00:01:00'):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, 17.)},
                23.,
                {"period": 2},
                "c",
                0.,
                0.,
                "my_test",
            ))

    assert isinstance(results[0], Result)
    assert results[0].state == state.OK
    assert results[0].summary == 'Temperature trend: +12.0°C per 2 min'


def test_check_trend_ok():

    with freezegun.freeze_time('1970-01-01 00:01:00'):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, 17.)},
                23.,
                {
                    "period": 2,
                    "trend_levels": (50.0, 55.0),
                    "trend_levels_lower": (-50.0, -55.5),
                },
                "c",
                0.,
                0.,
                "my_test",
            ))

    assert isinstance(results[0], Result)
    assert results[0].state == state.OK
    assert results[0].summary == 'Temperature trend: +12.0°C per 2 min'


def test_check_trend_warn_upper():

    with freezegun.freeze_time('1970-01-01 00:01:00'):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, 17.)},
                23.,
                {
                    "period": 2,
                    "trend_levels": (10.0, 15.0),
                    "trend_levels_lower": (-10.0, -15.0),
                },
                "c",
                0.,
                0.,
                "my_test",
            ))

    assert isinstance(results[0], Result)
    assert results[0].state == state.WARN
    assert results[
        0].summary == 'Temperature trend: +12.0°C per 2 min (warn/crit at +10.0°C per 2 min/+15.0°C per 2 min)'


def test_check_trend_crit_upper():

    with freezegun.freeze_time('1970-01-01 00:01:00'):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, 17.)},
                23.,
                {
                    "period": 2,
                    "trend_levels": (7.0, 10.0),
                    "trend_levels_lower": (-10.0, -15.0),
                },
                "c",
                0.,
                0.,
                "my_test",
            ))

    assert isinstance(results[0], Result)
    assert results[0].state == state.CRIT
    assert results[
        0].summary == 'Temperature trend: +12.0°C per 2 min (warn/crit at +7.0°C per 2 min/+10.0°C per 2 min)'


def test_check_trend_warn_lower():

    with freezegun.freeze_time('1970-01-01 00:01:00'):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, -17.)},
                -23.,
                {
                    "period": 2,
                    "trend_levels": (50.0, 55.0),
                    "trend_levels_lower": (-10.0, -15.0),
                },
                "c",
                0.,
                0.,
                "my_test",
            ))

    assert isinstance(results[0], Result)
    assert results[0].state == state.WARN
    assert results[
        0].summary == 'Temperature trend: -12.0°C per 2 min (warn/crit below -10.0°C per 2 min/-15.0°C per 2 min)'


def test_check_trend_crit_lower():

    with freezegun.freeze_time('1970-01-01 00:01:00'):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, -17.)},
                -23.,
                {
                    "period": 2,
                    "trend_levels": (50.0, 55.0),
                    "trend_levels_lower": (-5.0, -10.0),
                },
                "c",
                0.,
                0.,
                "my_test",
            ))

    assert isinstance(results[0], Result)
    assert results[0].state == state.CRIT
    assert results[
        0].summary == 'Temperature trend: -12.0°C per 2 min (warn/crit below -5.0°C per 2 min/-10.0°C per 2 min)'


def test_check_trend_time_period_ok():

    with freezegun.freeze_time('1970-01-01 00:01:00'):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, 5.)},
                10.,
                {
                    "period": 1,
                    "trend_levels": (50.0, 55.0),
                    "trend_levels_lower": (-50.0, -55.0),
                    "trend_timeleft": (5.0, 2.0),
                },
                "c",
                40.0,
                0.0,
                "my_test",
            ))

    assert isinstance(results[0], Result)
    assert results[0].state == state.OK
    assert results[0].summary == 'Temperature trend: +5.0°C per 1 min'

    assert isinstance(results[1], Result)
    assert results[1].state == state.OK
    assert results[1].summary == 'Time until temperature limit reached: 6 minutes 0 seconds'


def test_check_trend_time_period_warn_upper():

    with freezegun.freeze_time('1970-01-01 00:01:00'):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, 5.)},
                10.,
                {
                    "period": 1,
                    "trend_levels": (50.0, 55.0),
                    "trend_levels_lower": (-50.0, -55.0),
                    "trend_timeleft": (7.0, 2.0),
                },
                "c",
                40.0,
                0.0,
                "my_test",
            ))

    assert isinstance(results[0], Result)
    assert results[0].state == state.OK
    assert results[0].summary == 'Temperature trend: +5.0°C per 1 min'

    assert isinstance(results[1], Result)
    assert results[1].state == state.WARN
    assert results[
        1].summary == 'Time until temperature limit reached: 6 minutes 0 seconds (warn/crit below 7 minutes 0 seconds/2 minutes 0 seconds)'


def test_check_trend_time_period_crit_upper():

    with freezegun.freeze_time('1970-01-01 00:01:00'):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, 5.)},
                10.,
                {
                    "period": 1,
                    "trend_levels": (50.0, 55.0),
                    "trend_levels_lower": (-50.0, -55.0),
                    "trend_timeleft": (8.0, 7.0),
                },
                "c",
                40.0,
                0.0,
                "my_test",
            ))

    assert isinstance(results[0], Result)
    assert results[0].state == state.OK
    assert results[0].summary == 'Temperature trend: +5.0°C per 1 min'

    assert isinstance(results[1], Result)
    assert results[1].state == state.CRIT
    assert results[
        1].summary == 'Time until temperature limit reached: 6 minutes 0 seconds (warn/crit below 8 minutes 0 seconds/7 minutes 0 seconds)'


def test_check_trend_time_period_warn_lower():

    with freezegun.freeze_time('1970-01-01 00:01:00'):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, 10.)},
                5.,
                {
                    "period": 1,
                    "trend_levels": (50.0, 55.0),
                    "trend_levels_lower": (-50.0, -55.0),
                    "trend_timeleft": (8.0, 6.0),
                },
                "c",
                40.0,
                -30.0,
                "my_test",
            ))

    assert isinstance(results[0], Result)
    assert results[0].state == state.OK
    assert results[0].summary == 'Temperature trend: -5.0°C per 1 min'

    assert isinstance(results[1], Result)
    assert results[1].state == state.WARN
    assert results[
        1].summary == 'Time until temperature limit reached: 7 minutes 0 seconds (warn/crit below 8 minutes 0 seconds/6 minutes 0 seconds)'


def test_check_trend_time_period_crit_lower():

    with freezegun.freeze_time('1970-01-01 00:01:00'):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, 10.)},
                5.,
                {
                    "period": 1,
                    "trend_levels": (50.0, 55.0),
                    "trend_levels_lower": (-50.0, -55.0),
                    "trend_timeleft": (8.0, 6.0),
                },
                "c",
                40.0,
                -10.0,
                "my_test",
            ))

    assert isinstance(results[0], Result)
    assert results[0].state == state.OK
    assert results[0].summary == 'Temperature trend: -5.0°C per 1 min'

    assert isinstance(results[1], Result)
    assert results[1].state == state.CRIT
    assert results[
        1].summary == 'Time until temperature limit reached: 3 minutes 0 seconds (warn/crit below 8 minutes 0 seconds/6 minutes 0 seconds)'


def test_check_trend_time_period_zero_lower_bound():

    with freezegun.freeze_time('1970-01-01 00:01:00'):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, 10.)},
                5.,
                {
                    "period": 1,
                    "trend_levels": (50.0, 55.0),
                    "trend_levels_lower": (-50.0, -55.0),
                    "trend_timeleft": (8.0, 6.0),
                },
                "c",
                40.0,
                0.0,
                "my_test",
            ))

    assert isinstance(results[0], Result)
    assert results[0].state == state.OK
    assert results[0].summary == 'Temperature trend: -5.0°C per 1 min'

    assert isinstance(results[1], Result)
    assert results[1].state == state.CRIT
    assert results[
        1].summary == 'Time until temperature limit reached: 1 minute 0 seconds (warn/crit below 8 minutes 0 seconds/6 minutes 0 seconds)'


def test_check_temperature_simple():

    results = list(
        temperature.check_temperature(
            23.0,
            None,
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=None,
            dev_levels_lower=None,
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == 23.0
    assert results[0].levels == (None, None)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.OK
    assert results[1].summary == 'Temperature: 23.0°C'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[
        2].details == 'Configuration: prefer user levels over device levels (no levels found)'


def test_check_temperature_user_levels_ok():

    results = list(
        temperature.check_temperature(
            23.0,
            {
                'levels': (26.0, 30.0),
            },
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=None,
            dev_levels_lower=None,
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == 23.0
    assert results[0].levels == (26.0, 30.0)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.OK
    assert results[1].summary == 'Temperature: 23.0°C'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[
        2].details == 'Configuration: prefer user levels over device levels (used user levels)'


def test_check_temperature_user_levels_warn_upper():

    results = list(
        temperature.check_temperature(
            23.0,
            {
                'levels': (23.0, 30.0),
            },
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=None,
            dev_levels_lower=None,
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == 23.0
    assert results[0].levels == (23.0, 30.0)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.WARN
    assert results[1].summary == 'Temperature: 23.0°C (warn/crit at 23.0°C/30.0°C)'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[
        2].details == 'Configuration: prefer user levels over device levels (used user levels)'


def test_check_temperature_user_levels_crit_upper():

    results = list(
        temperature.check_temperature(
            30.0,
            {
                'levels': (23.0, 30.0),
            },
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=None,
            dev_levels_lower=None,
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == 30.0
    assert results[0].levels == (23.0, 30.0)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.CRIT
    assert results[1].summary == 'Temperature: 30.0°C (warn/crit at 23.0°C/30.0°C)'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[
        2].details == 'Configuration: prefer user levels over device levels (used user levels)'


def test_check_temperature_user_levels_warn_lower():

    results = list(
        temperature.check_temperature(
            -1.0,
            {
                'levels_lower': (0.0, -15.0),
            },
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=None,
            dev_levels_lower=None,
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == -1.0
    assert results[0].levels == (None, None)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.WARN
    assert results[1].summary == 'Temperature: -1.0°C (warn/crit below 0.0°C/-15.0°C)'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[
        2].details == 'Configuration: prefer user levels over device levels (used user levels)'


def test_check_temperature_user_levels_crit_lower():

    results = list(
        temperature.check_temperature(
            -16.0,
            {
                'levels_lower': (0.0, -15.0),
            },
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=None,
            dev_levels_lower=None,
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == -16.0
    assert results[0].levels == (None, None)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.CRIT
    assert results[1].summary == 'Temperature: -16.0°C (warn/crit below 0.0°C/-15.0°C)'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[
        2].details == 'Configuration: prefer user levels over device levels (used user levels)'


def test_check_temperature_output_unit():

    results = list(
        temperature.check_temperature(
            10.0,
            {
                'output_unit': 'f',
            },
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=None,
            dev_levels_lower=None,
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == 10.0
    assert results[0].levels == (None, None)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.OK
    assert results[1].summary == 'Temperature: 50.0°F'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[
        2].details == 'Configuration: prefer user levels over device levels (no levels found)'


def test_check_temperature_input_unit():

    results = list(
        temperature.check_temperature(
            50.0,
            {
                'input_unit': 'f',
            },
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=None,
            dev_levels_lower=None,
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == 10.0
    assert results[0].levels == (None, None)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.OK
    assert results[1].summary == 'Temperature: 10.0°C'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[
        2].details == 'Configuration: prefer user levels over device levels (no levels found)'


def test_check_temperature_unique_name():

    results = list(
        temperature.check_temperature(
            10.0,
            None,
            unique_name='my_test',
            value_store=None,
            dev_unit=None,
            dev_levels=None,
            dev_levels_lower=None,
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == 10.0
    assert results[0].levels == (None, None)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.OK
    assert results[1].summary == 'Temperature: 10.0°C'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[
        2].details == 'Configuration: prefer user levels over device levels (no levels found)'


def test_check_temperature_value_store():

    results = list(
        temperature.check_temperature(
            10.0,
            None,
            unique_name=None,
            value_store='temp.my_test',
            dev_unit=None,
            dev_levels=None,
            dev_levels_lower=None,
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == 10.0
    assert results[0].levels == (None, None)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.OK
    assert results[1].summary == 'Temperature: 10.0°C'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[
        2].details == 'Configuration: prefer user levels over device levels (no levels found)'


def test_check_temperature_device_levels_ok():

    results = list(
        temperature.check_temperature(
            10.0,
            None,
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=(54.0, 70.0),
            dev_levels_lower=None,
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == 10.0
    assert results[0].levels == (54.0, 70.0)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.OK
    assert results[1].summary == 'Temperature: 10.0°C'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[
        2].details == 'Configuration: prefer user levels over device levels (used device levels)'


def test_check_temperature_device_levels_warn_upper():

    results = list(
        temperature.check_temperature(
            10.0,
            None,
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=(10.0, 15.0),
            dev_levels_lower=None,
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == 10.0
    assert results[0].levels == (10.0, 15.0)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.WARN
    assert results[1].summary == 'Temperature: 10.0°C (warn/crit at 10.0°C/15.0°C)'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[
        2].details == 'Configuration: prefer user levels over device levels (used device levels)'


def test_check_temperature_device_levels_crit_upper():

    results = list(
        temperature.check_temperature(
            18.0,
            None,
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=(10.0, 15.0),
            dev_levels_lower=None,
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == 18.0
    assert results[0].levels == (10.0, 15.0)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.CRIT
    assert results[1].summary == 'Temperature: 18.0°C (warn/crit at 10.0°C/15.0°C)'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[
        2].details == 'Configuration: prefer user levels over device levels (used device levels)'


def test_check_temperature_device_levels_warn_lower():

    results = list(
        temperature.check_temperature(
            0.0,
            None,
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=(10.0, 15.0),
            dev_levels_lower=(1.0, -15.0),
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == 0.0
    assert results[0].levels == (10.0, 15.0)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.WARN
    assert results[1].summary == 'Temperature: 0.0°C (warn/crit below 1.0°C/-15.0°C)'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[
        2].details == 'Configuration: prefer user levels over device levels (used device levels)'


def test_check_temperature_device_levels_crit_lower():

    results = list(
        temperature.check_temperature(
            -20.0,
            None,
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=(10.0, 15.0),
            dev_levels_lower=(1.0, -15.0),
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == -20.0
    assert results[0].levels == (10.0, 15.0)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.CRIT
    assert results[1].summary == 'Temperature: -20.0°C (warn/crit below 1.0°C/-15.0°C)'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[
        2].details == 'Configuration: prefer user levels over device levels (used device levels)'


def test_check_temperature_use_user_levels():

    results = list(
        temperature.check_temperature(
            -20.0,
            {
                'levels': (50.0, 75.0),
                'levels_lower': (-25.0, -30.0),
                'device_levels_handling': 'usr',
            },
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=(10.0, 15.0),
            dev_levels_lower=(1.0, -15.0),
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == -20.0
    assert results[0].levels == (50.0, 75.0)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.OK
    assert results[1].summary == 'Temperature: -20.0°C'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[2].details == 'Configuration: only use user levels'


def test_check_temperature_use_device_levels():

    results = list(
        temperature.check_temperature(
            -20.0,
            {
                'levels': (50.0, 75.0),
                'levels_lower': (-25.0, -30.0),
                'device_levels_handling': 'dev',
            },
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=(10.0, 15.0),
            dev_levels_lower=(1.0, -15.0),
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == -20.0
    assert results[0].levels == (10.0, 15.0)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.CRIT
    assert results[1].summary == 'Temperature: -20.0°C (warn/crit below 1.0°C/-15.0°C)'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[2].details == 'Configuration: only use device levels'


def test_check_temperature_default_device_levels():

    results = list(
        temperature.check_temperature(
            -20.0,
            {
                'levels': (50.0, 75.0),
                'levels_lower': (-25.0, -30.0),
                'device_levels_handling': 'devdefault',
            },
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=(10.0, 15.0),
            dev_levels_lower=(1.0, -15.0),
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == -20.0
    assert results[0].levels == (10.0, 15.0)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.CRIT
    assert results[1].summary == 'Temperature: -20.0°C (warn/crit below 1.0°C/-15.0°C)'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[
        2].details == 'Configuration: prefer device levels over user levels (used device levels)'


def test_check_temperature_default_user_levels():

    results = list(
        temperature.check_temperature(
            -20.0,
            {
                'levels_lower': (-25.0, -30.0),
                'device_levels_handling': 'usrdefault',
            },
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=None,
            dev_levels_lower=None,
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == -20.0
    assert results[0].levels == (None, None)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.OK
    assert results[1].summary == 'Temperature: -20.0°C'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[
        2].details == 'Configuration: prefer user levels over device levels (used user levels)'


def test_check_temperature_use_device_default_no_levels():

    results = list(
        temperature.check_temperature(
            -20.0,
            {
                'device_levels_handling': 'devdefault',
            },
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=None,
            dev_levels_lower=None,
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == -20.0
    assert results[0].levels == (None, None)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.OK
    assert results[1].summary == 'Temperature: -20.0°C'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[
        2].details == 'Configuration: prefer device levels over user levels (no levels found)'


def test_check_temperature_use_user_default_device_levels():

    results = list(
        temperature.check_temperature(
            -20.0,
            {
                'device_levels_handling': 'usrdefault',
            },
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=None,
            dev_levels_lower=(1.0, -15.0),
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == -20.0
    assert results[0].levels == (None, None)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.CRIT
    assert results[1].summary == 'Temperature: -20.0°C (warn/crit below 1.0°C/-15.0°C)'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[
        2].details == 'Configuration: prefer user levels over device levels (used device levels)'


def test_check_temperature_use_user_default_user_levels():

    results = list(
        temperature.check_temperature(
            -20.0,
            {
                'levels_lower': (-25.0, -30.0),
                'device_levels_handling': 'usrdefault',
            },
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=(10.0, 15.0),
            dev_levels_lower=(1.0, -15.0),
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == -20.0
    assert results[0].levels == (None, None)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.OK
    assert results[1].summary == 'Temperature: -20.0°C'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[
        2].details == 'Configuration: prefer user levels over device levels (used user levels)'


def test_check_temperature_use_user_default_no_levels():

    results = list(
        temperature.check_temperature(
            -20.0,
            {
                'device_levels_handling': 'usrdefault',
            },
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=None,
            dev_levels_lower=None,
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == -20.0
    assert results[0].levels == (None, None)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.OK
    assert results[1].summary == 'Temperature: -20.0°C'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[
        2].details == 'Configuration: prefer user levels over device levels (no levels found)'


def test_check_temperature_show_worst():

    results = list(
        temperature.check_temperature(
            -20.0,
            {
                'levels': (50.0, 75.0),
                'levels_lower': (-25.0, -30.0),
                'device_levels_handling': 'worst',
            },
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=(10.0, 15.0),
            dev_levels_lower=(1.0, -15.0),
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == -20.0
    assert results[0].levels == (10.0, 15.0)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.CRIT
    assert results[1].summary == 'Temperature: -20.0°C (warn/crit below 1.0°C/-15.0°C)'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[2].details == 'Configuration: show most critical state'


def test_check_temperature_show_best():

    results = list(
        temperature.check_temperature(
            -20.0,
            {
                'levels': (50.0, 75.0),
                'levels_lower': (-25.0, -30.0),
                'device_levels_handling': 'best',
            },
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=(10.0, 15.0),
            dev_levels_lower=(1.0, -15.0),
            dev_status=None,
            dev_status_name=None,
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == -20.0
    assert results[0].levels == (50.0, 75.0)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.OK
    assert results[1].summary == 'Temperature: -20.0°C'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[2].details == 'Configuration: show least critical state'


def test_check_temperature_device_status_override_best():

    results = list(
        temperature.check_temperature(
            -20.0,
            {
                'levels': (50.0, 75.0),
                'levels_lower': (0.0, -10.0),
                'device_levels_handling': 'best',
            },
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=(10.0, 15.0),
            dev_levels_lower=(-25.0, -30.0),
            dev_status=1,
            dev_status_name='banana',
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == -20.0
    assert results[0].levels == (10.0, 15.0)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.OK
    assert results[1].summary == 'Temperature: -20.0°C'

    assert isinstance(results[2], Result)
    assert results[2].state == state.WARN
    assert results[2].summary == 'State on device: banana'

    assert isinstance(results[3], Result)
    assert results[3].state == state.OK
    assert results[3].summary == ''
    assert results[3].details == 'Configuration: show least critical state'


def test_check_temperature_device_status_override_worst():

    results = list(
        temperature.check_temperature(
            5.0,
            {
                'levels': (50.0, 75.0),
                'levels_lower': (0.0, -10.0),
                'device_levels_handling': 'worst',
            },
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=(10.0, 15.0),
            dev_levels_lower=(1.0, -15.0),
            dev_status=2,
            dev_status_name='banana',
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == 5.0
    assert results[0].levels == (10.0, 15.0)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.OK
    assert results[1].summary == 'Temperature: 5.0°C'

    assert isinstance(results[2], Result)
    assert results[2].state == state.CRIT
    assert results[2].summary == 'State on device: banana'

    assert isinstance(results[3], Result)
    assert results[3].state == state.OK
    assert results[3].summary == ''
    assert results[3].details == 'Configuration: show most critical state'


def test_check_temperature_device_status_override_ok():

    results = list(
        temperature.check_temperature(
            5.0,
            {
                'levels': (5.0, 10.0),
                'levels_lower': (0.0, -10.0),
                'device_levels_handling': 'best',
            },
            unique_name=None,
            value_store=None,
            dev_unit=None,
            dev_levels=(20.0, 25.0),
            dev_levels_lower=(1.0, -15.0),
            dev_status=0,
            dev_status_name='banana',
        ))

    assert isinstance(results[0], Metric)
    assert results[0].name == 'temp'
    assert results[0].value == 5.0
    assert results[0].levels == (20.0, 25.0)
    assert results[0].boundaries == (None, None)

    assert isinstance(results[1], Result)
    assert results[1].state == state.OK
    assert results[1].summary == 'Temperature: 5.0°C'

    assert isinstance(results[2], Result)
    assert results[2].state == state.OK
    assert results[2].summary == ''
    assert results[2].details == 'State on device: banana'

    assert isinstance(results[3], Result)
    assert results[3].state == state.OK
    assert results[3].summary == ''
    assert results[3].details == 'Configuration: show least critical state'
