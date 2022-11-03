#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import on_time

from cmk.gui.availability import layout_timeline


@pytest.mark.parametrize(
    "what,timeline_rows,considered_duration,avoptions,style,expected",
    [
        pytest.param(
            "service",
            [
                (
                    {
                        "site": "stable",
                        "host_name": "stable",
                        "service_description": "CPU load",
                        "duration": 900,
                        "from": 1667381700,
                        "until": 1667382600,
                        "state": -1,
                        "host_down": 0,
                        "in_downtime": 0,
                        "in_host_downtime": 0,
                        "in_notification_period": 1,
                        "in_service_period": 1,
                        "is_flapping": 0,
                        "log_output": "",
                    },
                    "unmonitored",
                ),
                (
                    {
                        "site": "stable",
                        "host_name": "stable",
                        "service_description": "CPU load",
                        "duration": 900,
                        "from": 1667468100,
                        "until": 1667469000,
                        "state": 0,
                        "host_down": 0,
                        "in_downtime": 0,
                        "in_host_downtime": 0,
                        "in_notification_period": 1,
                        "in_service_period": 1,
                        "is_flapping": 0,
                        "log_output": "15 min load: 4.38, 15 min load per core: 0.55 (8 cores)",
                    },
                    "ok",
                ),
                (
                    {
                        "site": "stable",
                        "host_name": "stable",
                        "service_description": "CPU load",
                        "duration": 900,
                        "from": 1667554500,
                        "until": 1667555400,
                        "state": 0,
                        "host_down": 0,
                        "in_downtime": 0,
                        "in_host_downtime": 0,
                        "in_notification_period": 1,
                        "in_service_period": 1,
                        "is_flapping": 0,
                        "log_output": "15 min load: 4.38, 15 min load per core: 0.55 (8 cores)",
                    },
                    "ok",
                ),
            ],
            2700,
            {
                "range": ((1667379750, 1667566950), "The last 2 days 4 hours"),
                "rangespec": ("age", 187200),
                "labelling": [],
                "av_levels": None,
                "av_filter_outages": {"warn": 0.0, "crit": 0.0, "non-ok": 0.0},
                "outage_statistics": ([], []),
                "av_mode": False,
                "service_period": "honor",
                "notification_period": "ignore",
                "grouping": None,
                "dateformat": "yyyy-mm-dd hh:mm:ss",
                "timeformat": ("perc", "percentage_2", "seconds"),
                "short_intervals": 0,
                "dont_merge": False,
                "summary": "sum",
                "show_timeline": False,
                "timelimit": 30,
                "logrow_limit": 5000,
                "downtimes": {"include": "honor", "exclude_ok": False},
                "consider": {"flapping": True, "host_down": True, "unmonitored": True},
                "host_state_grouping": {"unreach": "unreach"},
                "state_grouping": {"warn": "warn", "unknown": "unknown", "host_down": "host_down"},
            },
            "standalone",
            [
                (None, "", 1.0416666666666667, "unmonitored"),
                (
                    0,
                    "From 2022-11-02 10:35:00 until 2022-11-02 10:50:00 (33.33%) During this time period no monitoring data is available",
                    0.9735576923076923,
                    "unmonitored",
                ),
                (None, "", 45.67307692307692, "unmonitored"),
                (
                    1,
                    "From 2022-11-03 10:35:00 until 2022-11-03 10:50:00 (33.33%) OK - 15 min load: 4.38, 15 min load per core: 0.55 (8 cores)",
                    0.9735576923076923,
                    "state0",
                ),
                (None, "", 45.67307692307692, "unmonitored"),
                (
                    2,
                    "From 2022-11-04 10:35:00 until 2022-11-04 10:50:00 (33.33%) OK - 15 min load: 4.38, 15 min load per core: 0.55 (8 cores)",
                    0.9735576923076923,
                    "state0",
                ),
                (None, "", 6.169871794871795, "unmonitored"),
            ],
            id="Timeline based on service times",
        ),
    ],
)
def test_layout_timeline_spans(
    what,
    timeline_rows,
    considered_duration,
    avoptions,
    style,
    expected,
):
    with on_time("2022-11-04 14:02:30,439", "CET"):
        assert (
            layout_timeline(
                what,
                timeline_rows,
                considered_duration,
                avoptions,
                style,
            )["spans"]
            == expected
        )
