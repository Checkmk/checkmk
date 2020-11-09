#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib import Check  # type: ignore[import]
from checktestlib import DiscoveryResult, assertDiscoveryResultsEqual, \
                         BasicCheckResult, CheckResult, assertCheckResultsEqual

pytestmark = pytest.mark.checks

meinberg_lantime_1 = [[u'1', u'14', u'3', u'2', u'3', u'0', u'12', u'0', u'0', u'0', u'2012-06-30']]
meinberg_lantime_2 = [[u'1', u'28', u'3', u'1', u'52', u'62', u'100', u'101', u'127', u'0', u'0']]
meinberg_lantime_5 = [[
    u'1', u'14', u'3', u'1', u'150', u'6', u'8', u'0', u'0', u'1', u'not announced'
]]
meinberg_lantime_6 = [[
    u'1', u'30', u'3', u'1', u'155', u'0', u'8', u'0', u'0', u'0', u'2016-12-31'
]]


@pytest.mark.parametrize(
    "info,expected",
    [
        (meinberg_lantime_1, DiscoveryResult([])),  # GPS clocks are not covered here
        (meinberg_lantime_2, DiscoveryResult([('1', None)])),
    ])
@pytest.mark.usefixtures("config_load_all_checks")
def test_discovery_mbg_lantime_ng_refclock(info, expected):
    check = Check("mbg_lantime_ng_refclock")
    discovery = DiscoveryResult(check.run_discovery(info))
    assertDiscoveryResultsEqual(check, discovery, expected)


@pytest.mark.parametrize("info,item,params,expected", [
    (meinberg_lantime_2, '1', (3, 3),
     CheckResult([
         BasicCheckResult(0, 'Type: pzf600, Usage: primary, State: synchronized (LW sync)', None),
         BasicCheckResult(0, 'Field strength: 80%', [('field_strength', 80.0)]),
         BasicCheckResult(0, 'Correlation: 62%', [('correlation', 62.0)]),
     ])),
])
@pytest.mark.usefixtures("config_load_all_checks")
def test_check_mbg_lantime_ng_refclock(info, item, params, expected):
    check = Check("mbg_lantime_ng_refclock")
    result = CheckResult(check.run_check(item, params, info))
    assertCheckResultsEqual(result, expected)


@pytest.mark.parametrize(
    "info,expected",
    [
        (meinberg_lantime_1, DiscoveryResult([('1', 'mbg_lantime_refclock_default_levels')])),
        (meinberg_lantime_2, DiscoveryResult([])),  # don't discover GPS clocks
        (meinberg_lantime_5, DiscoveryResult([('1', 'mbg_lantime_refclock_default_levels')])),
        (meinberg_lantime_6, DiscoveryResult([('1', 'mbg_lantime_refclock_default_levels')])),
    ])
@pytest.mark.usefixtures("config_load_all_checks")
def test_discovery_mbg_lantime_ng_refclock_gps(info, expected):
    check = Check("mbg_lantime_ng_refclock.gps")
    discovery = DiscoveryResult(check.run_discovery(info))
    assertDiscoveryResultsEqual(check, discovery, expected)


@pytest.mark.parametrize(
    "info,item,params,expected",
    [
        (
            meinberg_lantime_1,
            '1',
            (3, 3),
            CheckResult([
                BasicCheckResult(
                    1,
                    'Type: gps170, Usage: primary, State: not synchronized (GPS antenna disconnected)',
                    None),
                BasicCheckResult(0, 'Next leap second: 2012-06-30', None),
                BasicCheckResult(2, 'Satellites: 0/12 (warn/crit below 3/3)', None)
            ]),
        ),
        (
            meinberg_lantime_5,
            '1',
            (3, 3),
            CheckResult([
                BasicCheckResult(
                    0, 'Type: gps170, Usage: primary, State: synchronized (MRS GPS sync)', None),
                BasicCheckResult(0, 'Next leap second: not announced', None),
                BasicCheckResult(0, 'Satellites: 6/8', None)
            ]),
        ),
        (
            meinberg_lantime_6,
            '1',
            (3, 3),
            CheckResult([
                BasicCheckResult(
                    0, 'Type: gps180, Usage: primary, State: synchronized (MRS NTP sync)', None),
                BasicCheckResult(0, 'Next leap second: 2016-12-31', None),
                # satellites are not checked here
            ]),
        ),
    ])
@pytest.mark.usefixtures("config_load_all_checks")
def test_check_mbg_lantime_ng_refclock_gps(info, item, params, expected):
    check = Check("mbg_lantime_ng_refclock.gps")
    result = CheckResult(check.run_check(item, params, info))
    assertCheckResultsEqual(result, expected)
