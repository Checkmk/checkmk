#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# coding=utf-8
# yapf: disable
import datetime as dt
from typing import Any, Mapping, NamedTuple

import freezegun
import pytest

from tests.testlib import Check

from .checktestlib import assertCheckResultsEqual, CheckResult, mock_item_state


@pytest.mark.parametrize(
    "params,kwargs,expected",
    [
        # The following inputs and outputs are expected to succeed
        # as no levels are checked, or the levels are OK.
        ((5, {}, "Foo"),
         {},
         (0, u'5 \xb0C', [('temp', 5, None, None)])),

        ((5, {'device_levels_handling': 'best'}, "Foo"),
         {'dev_status': 1},
         (0, u'5 \xb0C', [('temp', 5, None, None)])),

        ((5, {"device_levels_handling": "dev"}, "Foo"),
         {},
         (0, u'5 \xb0C', [('temp', 5, None, None)])),

        ((5, {"device_levels_handling": "dev"}, "Foo"),
         {
             'dev_levels_lower': (None, None)
         },
         (0, u'5 \xb0C', [('temp', 5, None, None)])),

        ((5, {"device_levels_handling": "dev"}, "Foo"),
         {'dev_levels_lower': (0, 0)},
         (0, u'5 \xb0C', [('temp', 5, None, None)])),

        ((5,
          {
              'device_levels_handling': 'usrdefault',
              'levels': (6, 6),
              'levels_lower': (None, None),
          },
          "Foo"),
         {'dev_status': 1},
         (0, u'5 \xb0C', [('temp', 5, 6, 6)])),

        # From here on, we will fail in different ways.
        # First, the device says it's borked.
        ((5, {}, "Foo"),
         {'dev_status': 1, 'dev_status_name': 'Borked'},
         (1, u'5 \xb0C, Borked', [('temp', 5, None, None)])),

        # Then the device says its borked but in a different mode.
        ((5,
          {
              'device_levels_handling': 'usrdefault',
              'levels': (None, None),
              'levels_lower': (None, None),
          },
          "Foo"),
         {'dev_status': 1},
         (1, u'5 \xb0C', [('temp', 5, None, None)])),

        # Now it fails and the levels fail in various modes.
        ((5,
          {
              'device_levels_handling': 'usrdefault',
              'levels': (4, 4),
              'levels_lower': (None, None),
          },
          "Foo"),
         {'dev_status': 1},
         (2, u'5 \xb0C (warn/crit at 4/4 \xb0C)', [('temp', 5, 4, 4)])),

        ((5,
          {
              'device_levels_handling': 'usrdefault',
              'levels': (None, None),
              'levels_lower': (6, 6),
          },
          "Foo"),
         {'dev_status': 1},
         (2, u'5 \xb0C (warn/crit below 6/6 \xb0C)', [('temp', 5, None, None)])),

        ((5, {'device_levels_handling': 'best', 'levels': (4, 4)}, "Foo"),
         {'dev_status': 1},
         (1, u'5 \xb0C (warn/crit at 4/4 \xb0C)', [('temp', 5, 4, 4)])),

        ((5,
          {
              'device_levels_handling': 'usr',
              'levels': (4, 4),
              'levels_lower': (4, 4)
          }, "Foo"),
         {'dev_status': 1, 'dev_levels': (4, 4), 'dev_levels_lower': (4, 4)},
         (2, u'5 \xb0C (warn/crit at 4/4 \xb0C) (warn/crit below 4/4 \xb0C)', [('temp', 5, 4, 4)])),

        ((5,
          {
              'device_levels_handling': 'usr',
              'levels': (5, 6),
              'levels_lower': (4, 4)
          }, "Foo"),
         {'dev_status': 1, 'dev_levels': (4, 4), 'dev_levels_lower': (4, 4)},
         (1, u'5 \xb0C (warn/crit at 5/6 \xb0C) (warn/crit below 4/4 \xb0C)', [('temp', 5, 5, 6)])),


        ((5,
          {
              'device_levels_handling': 'worst',
              'levels': (4, 4),
              'levels_lower': (4, 4)
          }, "Foo"),
         {'dev_status': 1},
         (2, u'5 \xb0C (warn/crit at 4/4 \xb0C) (warn/crit below 4/4 \xb0C)', [('temp', 5, 4, 4)])),

        ((5,
          {
              'device_levels_handling': 'worst',
              'levels': (4, 4),
              'levels_lower': (4, 4)
          }, "Foo"),
         {'dev_status': 1, 'dev_levels': (4, 4), 'dev_levels_lower': (4, 4)},
         (2, u'5 \xb0C (warn/crit at 4/4 \xb0C) (warn/crit below 4/4 \xb0C) '
             u'(device warn/crit at 4/4 \xb0C) (device warn/crit below 4/4 \xb0C)',
          [('temp', 5, 4, 4)])),

        ((5, {'device_levels_handling': 'worst'}, "Foo"),
         {'dev_status': 1},
         (1, u'5 \xb0C', [('temp', 5, None, None)])),

        ((5, {"device_levels_handling": "dev"}, "Foo"),
         {'dev_levels': (4, 4)},
         (2, u'5 \xb0C (device warn/crit at 4/4 \xb0C)', [('temp', 5, 4, 4)])),

        ((5, {"device_levels_handling": "dev"}, "Foo"),
         {'dev_levels_lower': (6, 6)},
         (2, u'5 \xb0C (device warn/crit below 6/6 \xb0C)', [('temp', 5, None, None)])),

        # Crashed previously
        ((5, {"device_levels_handling": "dev"}, "Foo"),
         {
             'dev_levels': (4, 4),
             'dev_levels_lower': (None, None),
         },
         (2, u'5 \xb0C (device warn/crit at 4/4 \xb0C)', [('temp', 5, 4, 4)])),

        # Crashed as well
        ((5, {"device_levels_handling": "dev"}, "Foo"),
         {
             'dev_levels': (None, None),
             'dev_levels_lower': (6, 6),
         },
         (2, u'5 \xb0C (device warn/crit below 6/6 \xb0C)', [('temp', 5, None, None)])),
    ],
)
def test_check_temperature(params, kwargs, expected):
    check = Check('acme_temp')
    check_temperature = check.context['check_temperature']
    result = check_temperature(*params, **kwargs)
    assertCheckResultsEqual(CheckResult(result), CheckResult(expected))


def unix_ts(datetime_obj, epoch=dt.datetime(1970, 1, 1)):
    return (datetime_obj - epoch).total_seconds()


class Entry(NamedTuple):
    reading:float
    growth:float
    seconds_elapsed:float
    wato_dict: Mapping[str,Any]
    expected:Any

_WATO_DICT = {
    'period': 5,
    'trend_levels': (5, 10),
    'trend_levels_lower': (5, 10),
    'trend_timeleft': (240, 120),
}


@pytest.mark.parametrize(
    "test_case",
    [
        Entry(
            reading=5,
            growth=0.5,
            seconds_elapsed=10 * 60,
            wato_dict=_WATO_DICT,
            expected=(0, 'rate: +0.2/5 min'),
        ),
        Entry(
            reading=1,
            growth=6,
            seconds_elapsed=10 * 60,
            wato_dict=_WATO_DICT,
            expected=(1, 'rate: +3.0/5 min, 2h 35m until temp limit reached(!)'),
        ),
        Entry(
            reading=5,
            growth=22,
            seconds_elapsed=10 * 60,
            wato_dict=_WATO_DICT,
            expected=(2, 'rate: +11.0/5 min, rising faster than 10/5 min(!!), '
                         '33 minutes until temp limit reached(!!)')
        ),

        # No "minutes remaining" on downward slope calculated?
        Entry(
            reading=95,
            growth=-22,
            seconds_elapsed=10 * 60,
            wato_dict=_WATO_DICT,
            expected=(2, 'rate: -11.0/5 min, falling faster than -10/5 min(!!)'),
        ),

        # Does this even make sense?!?!
        Entry(
            reading=5,
            growth=200,
            seconds_elapsed=10 * 60,
            wato_dict=_WATO_DICT,
            expected=(2, 'rate: +100.0/5 min, rising faster than 10/5 min(!!), '
                         '-5 minutes until temp limit reached(!!)')
        ),

        # Are the effects of last two test cases related somehow?
    ]
)
def test_check_temperature_trend(test_case):
    check = Check('acme_temp')
    check_trend = check.context['check_temperature_trend']

    time = dt.datetime(2014, 1, 1, 0, 0, 0)

    state = {
        'temp.foo.delta': (unix_ts(time), test_case.reading),
        'temp.foo.trend': (0, 0)
    }

    with mock_item_state(state):
        with freezegun.freeze_time(time + dt.timedelta(seconds=test_case.seconds_elapsed)):
            result = check_trend(test_case.reading + test_case.growth,
                                 test_case.wato_dict, 'c',
                                 100,  # crit, don't boil
                                 0,  # crit_lower, don't freeze over
                                 'foo')
            assertCheckResultsEqual(CheckResult(result), CheckResult(test_case.expected))


@pytest.mark.parametrize(
    "test_case",
    [
        Entry(
            reading=5,
            growth=0.5,
            seconds_elapsed=10 * 60,
            wato_dict=_WATO_DICT,
            expected=(0, u'5.5 \xb0C, rate: +0.2/5 min', [('temp', 5.5, 100.0, 100.0)]),
        ),
    ]
)
def test_check_temperature_called(test_case):
    check = Check('acme_temp')
    check_temperature = check.context['check_temperature']
    time = dt.datetime(2014, 1, 1, 0, 0, 0)

    state = {
        'temp.foo.delta': (unix_ts(time), test_case.reading),
        'temp.foo.trend': (0, 0)
    }

    with mock_item_state(state):
        with freezegun.freeze_time(time + dt.timedelta(seconds=test_case.seconds_elapsed)):
            # Assuming atmospheric pressure...
            result = check_temperature(
                test_case.reading + test_case.growth,
                {
                    'device_level_handling': 'dev',
                    'trend_compute': test_case.wato_dict,
                },
                'foo',
                dev_unit='c',
                dev_levels=(100, 100),  # don't boil
                dev_levels_lower=(0, 0),  # don't freeze over
            )
            assertCheckResultsEqual(CheckResult(result), CheckResult(test_case.expected))
