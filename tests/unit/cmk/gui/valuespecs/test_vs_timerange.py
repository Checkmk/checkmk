#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

import cmk.gui.valuespec as vs


@pytest.mark.parametrize(
    "entry, result",
    [
        ("m0", ((1567296000, 1567702200), "September 2019")),
        ("m1", ((1564617600, 1567296000), "August 2019")),
        ("m3", ((1559347200, 1567296000), "June 2019 — August 2019")),
        ("y1", ((1514764800, 1546300800), "2018")),
        ("y0", ((1546300800, 1567702200), "2019")),
        ("4h", ((1567687800, 1567702200), "Last 4 hours")),
        (None, ((1567687800, 1567702200), "Last 4 hours")),
        (4 * 60 * 60, ((1567687800, 1567702200), "The last 4 hours")),
        ("25h", ((1567612200, 1567702200), "Last 25 hours")),
        ("8d", ((1567011000, 1567702200), "Last 8 days")),
        ("15d", ((1566406200, 1567702200), "Last 15 days")),
        ("35d", ((1564678200, 1567702200), "Last 35 days")),
        ("400d", ((1533142200, 1567702200), "Last 400 days")),
        ("d0", ((1567641600, 1567702200), "Today")),
        ("d1", ((1567555200, 1567641600), "Yesterday")),
        ("d7", ((1567036800, 1567123200), "2019-08-29")),
        ("d8", ((1566950400, 1567036800), "2019-08-28")),
        ("w0", ((1567382400, 1567702200), "This week")),
        ("w1", ((1566777600, 1567382400), "Last week")),
        ("w2", ((1566172800, 1566777600), "2019-08-19 — 2019-08-25")),
        (("date", (1536098400, 1567288800)), ((1536098400, 1567375200), "2018-09-04 — 2019-09-01")),
        (("until", 1577232000), ((1567702200, 1577232000), "2019-12-25")),
        (("time", (1549374782, 1567687982)), ((1549374782, 1567687982), "2019-02-05 — 2019-09-05")),
        (("age", 2 * 3600), ((1567695000, 1567702200), "The last 2 hours")),
        (("next", 3 * 3600), ((1567702200, 1567713000), "The next 3 hours")),
        # pnp compatibility:
        (("pnp_view", 99), ((1567687800, 1567702200), "Last 4 hours")),  # fallback
        (("pnp_view", 1), ((1567687800, 1567702200), "Last 4 hours")),
        (("pnp_view", 5), ((1533142200, 1567702200), "Last 400 days")),
    ],
)
def test_timerange(entry: vs.TimerangeValue, result: tuple[tuple[int, int], str]) -> None:
    with time_machine.travel(datetime.datetime(2019, 9, 5, 16, 50, tzinfo=ZoneInfo("UTC"))):
        assert vs.Timerange.compute_range(entry) == vs.ComputedTimerange(*result)


@pytest.mark.parametrize(
    "entry, refutcdate, result",
    [
        ("m0", "2019-09-15 15:09", ((1567296000, 1568560140), "September 2019")),
        ("m1", "2019-01-12", ((1543622400, 1546300800), "December 2018")),
        ("m-1", "2019-09-15 15:09", ((1567296000, 1569888000), "September 2019")),
        ("m2", "2019-02-12", ((1543622400, 1548979200), "December 2018 — January 2019")),
        ("m3", "2019-02-12", ((1541030400, 1548979200), "November 2018 — January 2019")),
        ("m-3", "2019-02-12", ((1548979200, 1556668800), "February 2019 — April 2019")),
        ("m-3", "2018-12-12", ((1543622400, 1551398400), "December 2018 — February 2019")),
        ("m6", "2019-02-12", ((1533081600, 1548979200), "August 2018 — January 2019")),
        ("m-6", "2019-02-12", ((1548979200, 1564617600), "February 2019 — July 2019")),
        ("y0", "2019-09-15", ((1546300800, 1568505600), "2019")),
        ("y1", "2019-09-15", ((1514764800, 1546300800), "2018")),
        ("y-1", "2019-09-15", ((1546300800, 1577836800), "2019")),
        ("f0", "2020-01-25", ((1577836800, 1577923200), "01/01/2020")),
        ("f1", "2020-01-25", ((1575158400, 1575244800), "01/12/2019")),
        ("l1", "2020-01-25", ((1577750400, 1577836800), "31/12/2019")),
        ("l1", "2020-03-25", ((1582934400, 1583020800), "29/02/2020")),
    ],
)
def test_timerange2(
    entry: vs.TimerangeValue, refutcdate: str, result: tuple[tuple[int, int], str]
) -> None:
    with time_machine.travel(
        datetime.datetime.fromisoformat(refutcdate).replace(tzinfo=ZoneInfo("UTC"))
    ):
        assert vs.Timerange.compute_range(entry) == vs.ComputedTimerange(*result)
