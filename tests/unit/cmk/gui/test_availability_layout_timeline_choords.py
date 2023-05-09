#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import calendar
import time

import pytest  # type: ignore[import]

from cmk.gui.availability import layout_timeline_choords

# In case this someday is better testable, we'll make sure to include
# the daylight savings time switch in tests
# Currentĺy, this is irrelevant due to the local -> UTC fixture below.
TEST_REFERENCE_TIME = calendar.timegm((2020, 3, 29, 2, 0, 0, 0, 0, 0))

HOURS = 3600

DAYS = 24 * HOURS


@pytest.fixture(autouse=True)
def fix_localaity(monkeypatch):
    monkeypatch.setattr(time, 'localtime', time.gmtime)
    monkeypatch.setattr(time, 'mktime', calendar.timegm)


def test_layout_timeline_choords_hour_scale():
    # hour scale: less than 12 hours
    time_range = (TEST_REFERENCE_TIME - 5.4 * HOURS, TEST_REFERENCE_TIME + 6.5 * HOURS)

    assert list(layout_timeline_choords(time_range)) == [
        (0.03361344537815126, '21:00'),
        (0.11764705882352941, '22:00'),
        (0.20168067226890757, '23:00'),
        (0.2857142857142857, '00:00'),
        (0.3697478991596639, '01:00'),
        (0.453781512605042, '02:00'),
        (0.5378151260504201, '03:00'),
        (0.6218487394957983, '04:00'),
        (0.7058823529411765, '05:00'),
        (0.7899159663865546, '06:00'),
        (0.8739495798319328, '07:00'),
        (0.957983193277311, '08:00'),
    ]


def test_layout_timeline_choords_2hour_scale():
    # 2hour scale: less than 24 hours
    time_range = (TEST_REFERENCE_TIME - 10.4 * HOURS, TEST_REFERENCE_TIME + 13.5 * HOURS)

    assert list(layout_timeline_choords(time_range)) == [
        (0.016736401673640166, 'Saturday 16:00'),
        (0.100418410041841, 'Saturday 18:00'),
        (0.18410041841004185, 'Saturday 20:00'),
        (0.26778242677824265, 'Saturday 22:00'),
        (0.3514644351464435, 'Sunday 00:00'),
        (0.4351464435146444, 'Sunday 02:00'),
        (0.5188284518828452, 'Sunday 04:00'),
        (0.602510460251046, 'Sunday 06:00'),
        (0.6861924686192469, 'Sunday 08:00'),
        (0.7698744769874477, 'Sunday 10:00'),
        (0.8535564853556485, 'Sunday 12:00'),
        (0.9372384937238494, 'Sunday 14:00'),
    ]


def test_layout_timeline_choords_6hour_scale():
    # 6hour scale: less than 48 hours
    time_range = (TEST_REFERENCE_TIME - 30.1 * HOURS, TEST_REFERENCE_TIME + 17.8 * HOURS)

    assert list(layout_timeline_choords(time_range)) == [
        (0.08559498956158663, 'Saturday 00:00'),
        (0.21085594989561587, 'Saturday 06:00'),
        (0.33611691022964507, 'Saturday 12:00'),
        (0.4613778705636743, 'Saturday 18:00'),
        (0.5866388308977035, 'Sunday 00:00'),
        (0.7118997912317327, 'Sunday 06:00'),
        (0.837160751565762, 'Sunday 12:00'),
        (0.9624217118997912, 'Sunday 18:00'),
    ]


def test_layout_timeline_choords_weeks_scale():
    # weeks scale: less than 60 days
    time_range = (TEST_REFERENCE_TIME - 32.08 * DAYS, TEST_REFERENCE_TIME + 27.5 * DAYS)

    assert list(layout_timeline_choords(time_range)) == [
        (0.08386483159897057, 'Monday, 02.03.'),
        (0.20135392189772855, 'Monday, 09.03.'),
        (0.31884301219648653, 'Monday, 16.03.'),
        (0.4363321024952445, 'Monday, 23.03.'),
        (0.5538211927940024, 'Monday, 30.03.'),
        (0.6713102830927604, 'Monday, 06.04.'),
        (0.7887993733915184, 'Monday, 13.04.'),
        (0.9062884636902764, 'Monday, 20.04.'),
    ]


def test_layout_timeline_choords_months_scale():
    time_range = (TEST_REFERENCE_TIME - 128.234 * DAYS, TEST_REFERENCE_TIME + 32 * DAYS)

    assert list(layout_timeline_choords(time_range)) == [
        (0.05086727327948887, 'December 2019'),
        (0.2443343277123821, 'January 2020'),
        (0.4378013821452753, 'February 2020'),
        (0.6187866911308851, 'March 2020'),
        (0.8122537455637784, 'April 2020'),
        (0.9994799272730298, 'May 2020'),
    ]
