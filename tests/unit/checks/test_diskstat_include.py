#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re  # noqa: F401 # pylint: disable=unused-import
import pytest  # type: ignore[import]

from checktestlib import CheckResult, assertCheckResultsEqual
from cmk.base.check_api import (  # noqa: F401 # pylint: disable=unused-import
    get_bytes_human_readable, check_levels,
)

import cmk.base.check_legacy_includes.diskstat
from cmk.base.check_legacy_includes.diskstat import *

pytestmark = pytest.mark.checks


def get_rate(_counter, _time, value):
    return value


def get_average(_counter, _time, value, _time_span):
    return round(value / 10.) * 10.


@pytest.mark.parametrize('args,expected_result', [
    ((1, '', {}, [None, None, 101, 201]),
     CheckResult((0, 'read: 50.50 kB/s, write: 100.50 kB/s', [
         ('read', 51712),
         ('write', 102912),
     ]))),
    ((1, '', {
        'average': 1
    }, [None, None, 101, 201]),
     CheckResult((0, 'read: 50.50 kB/s, write: 100.50 kB/s', [
         ('read', 51712),
         ('write', 102912),
         ('read.avg', 51710.0),
         ('write.avg', 102910.0),
     ]))),
])
def test_check_diskstat_line(monkeypatch, args, expected_result):
    monkeypatch.setattr(cmk.base.check_legacy_includes.diskstat, 'get_rate', get_rate)
    monkeypatch.setattr(cmk.base.check_legacy_includes.diskstat, 'get_average', get_average)
    actual_result = CheckResult(check_diskstat_line(*args))  # type: ignore[name-defined] # pylint: disable=undefined-variable
    assertCheckResultsEqual(actual_result, expected_result)


@pytest.mark.parametrize('info,expected_result', [
    ([["Node1", "Disk1", 1, 2], ["Node1", "Disk2", 1, 2]
     ], CheckResult((0, 'read: 1.00 kB/s, write: 2.00 kB/s', [
         ('read', 1024),
         ('write', 2048),
     ]))),
    ([["Node1", "Disk1", 1, 2], ["Node2", "Disk1", 1, 2]
     ], CheckResult((3, 'summary mode not supported in a cluster', []))),
])
def test_check_diskstat_generic_summary_clutster(monkeypatch, info, expected_result):
    monkeypatch.setattr(cmk.base.check_legacy_includes.diskstat, 'get_rate', get_rate)
    monkeypatch.setattr(cmk.base.check_legacy_includes.diskstat, 'get_average', get_average)
    actual_result = CheckResult(check_diskstat_generic("SUMMARY", {}, 0, info))  # type: ignore[name-defined] # pylint: disable=undefined-variable
    assertCheckResultsEqual(actual_result, expected_result)
