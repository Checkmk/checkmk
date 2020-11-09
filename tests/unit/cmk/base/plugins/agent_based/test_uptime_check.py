#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib import on_time

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import Parameters

from cmk.base.plugins.agent_based import uptime
from cmk.base.plugins.agent_based.utils import uptime as uptime_utils

# Mark all tests in this file as check related tests
pytestmark = pytest.mark.checks


@pytest.mark.parametrize("string, result", [
    ('22 day(s),  8:46', 1932360),
    ('4 day(s),  3 hr(s)', 356400),
    ('76 day(s), 26 min(s)', 6567960),
    ('1086 day(s)', 93830400),
    ('5 min(s)', 300),
    ('2 hr(s)', 7200),
])
def test_human_read_uptime(string, result):
    assert uptime.parse_human_read_uptime(string) == result


@pytest.mark.parametrize("section, do_discover", [
    (uptime_utils.Section(12, None), True),
    (uptime_utils.Section(None, None), False),
])
def test_uptime_discovery(section, do_discover):
    assert bool(list(uptime_utils.discover(section))) is do_discover


def test_uptime_check_basic():

    with on_time('2018-04-15 16:50', 'CET'):
        assert list(uptime_utils.check(Parameters({}), uptime_utils.Section(123, None))) == [
            Result(state=State.OK, summary='Up since Apr 15 2018 18:47:57'),
            Result(state=State.OK, summary='Uptime: 2 minutes 3 seconds'),
            Metric("uptime", 123.0),
        ]


def test_uptime_check_zero():
    with on_time('2018-04-15 16:50', 'CET'):
        assert list(uptime_utils.check(Parameters({}), uptime_utils.Section(0, None))) == [
            Result(state=State.OK, summary='Up since Apr 15 2018 18:50:00'),
            Result(state=State.OK, summary='Uptime: 0 seconds'),
            Metric("uptime", 0.0),
        ]


@pytest.mark.parametrize('info, reference', [
    (
        [
            [u'22731'],
            [u'[uptime_solaris_start]'],
            [u'SunOS', u'unknown', u'5.10', u'Generic_147148-26', u'i86pc', u'i386', u'i86pc'],
            [u'global'],
            [
                u'4:58pm', u'up', u'6:19,', u'2', u'users,', u'load', u'average:', u'0.18,',
                u'0.06,', u'0.03'
            ],
            [u'unix:0:system_misc:snaptime', u'22737.886916295'],
            [u'[uptime_solaris_end]'],
        ],
        [
            Result(state=State.OK, summary='Up since Apr 15 2018 12:31:09'),
            Result(state=State.OK, summary='Uptime: 6 hours 18 minutes'),
            Metric('uptime', 22731),
        ],
    ),
    (
        [
            [u'1122'],
            [u'[uptime_solaris_start]'],
            [u'SunOS', u'unknown', u'5.10', u'Generic_147148-26', u'i86pc', u'i386', u'i86pc'],
            [u'global'],
            [
                u'4:23pm', u'up', u'19', u'min(s),', u'2', u'users,', u'load', u'average:',
                u'0.03,', u'0.09,', u'0.09'
            ],
            [u'unix:0:system_misc:snaptime', u'1131.467157594'],
            [u'[uptime_solaris_end]'],
        ],
        [
            Result(state=State.OK, summary='Up since Apr 15 2018 18:31:18'),
            Result(state=State.OK, summary='Uptime: 18 minutes 42 seconds'),
            Metric('uptime', 1122),
        ],
    ),
    (
        [[u'1553086171'], [u'[uptime_solaris_start]'], [u'SunOS', u'Solaris', u'11.3', u'X86'],
         [u'non-global', u'zone'],
         [
             u'1:53pm', u'up', u'335', u'day(s),', u'23:13,', u'0', u'users,', u'load', u'average:',
             u'0.36,', u'0.34,', u'0.34'
         ], [u'unix:0:system_misc:snaptime', u'29027808.0471184'], [u'[uptime_solaris_end]']],
        [
            Result(state=State.OK, summary='Up since May 14 2017 19:33:11'),
            Result(state=State.OK, summary='Uptime: 335 days 23 hours'),
            Metric('uptime', 29027808.0471184),
        ],
    ),
    (
        [[u'54043590'], [u'[uptime_solaris_start]'],
         [u'SunOS', u'sveqdcmk01', u'5.10', u'Generic_150401-49', u'i86pc', u'i386', u'i86pc'],
         [u'sveqdcmk01'],
         [
             u'1:50pm', u'up', u'420', u'day(s),', u'21:05,', u'43', u'users,', u'load',
             u'average:', u'16.75,', u'19.66,', u'18.18'
         ], [u'unix:0:system_misc:snaptime', u'54048049.7479652'], [u'[uptime_solaris_end]']],
        [
            Result(
                state=State.UNKNOWN,
                summary=
                ('Your Solaris system gives inconsistent uptime information. Please get it fixed. '
                 'Uptime command: 420 days, 21:05:00; Kernel time since boot: 625 days, 12:06:30; '
                 'Snaptime: 625 days, 13:20:49.747965')),
        ],
    ),
    (
        [[u'1529194584'], [u'[uptime_solaris_start]'],
         [u'SunOS', u'sc000338', u'5.10', u'Generic_150400-61', u'sun4v', u'sparc', u'SUNW'],
         [u'sc000338'],
         [
             u'1:50pm', u'up', u'282', u'day(s),', u'13:40,', u'1', u'user,', u'load', u'average:',
             u'3.38,', u'3.44,', u'3.49'
         ], [u'unix:0:system_misc:snaptime', u'70236854.9797181'], [u'[uptime_solaris_end]']],
        [
            Result(
                state=State.UNKNOWN,
                summary=
                ('Your Solaris system gives inconsistent uptime information. Please get it fixed. '
                 'Uptime command: 282 days, 13:40:00; Kernel time since boot: 17699 days, 0:16:24; '
                 'Snaptime: 812 days, 22:14:14.979718')),
        ],
    ),
])
def test_uptime_solaris_inputs(info, reference):

    section = uptime.parse_uptime(info)
    assert section is not None

    # This time freeze has no correlation with the uptime of the test. It
    # is needed for the check output to always return the same infotext.
    # The true test happens on state and perfdata
    with on_time('2018-04-15 16:50', 'CET'):
        result = list(uptime_utils.check(Parameters({}), section))

    assert result == reference
