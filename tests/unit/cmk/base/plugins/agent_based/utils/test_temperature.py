#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import freezegun  # type: ignore[import]
import pytest  # type: ignore[import]

from cmk.base.plugins.agent_based.utils import temperature
from cmk.base.plugins.agent_based.agent_based_api.v0 import (
    Result,
    state,
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
