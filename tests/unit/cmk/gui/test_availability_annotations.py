#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import on_time

import cmk.utils.render

import cmk.gui.availability as availability


@pytest.mark.parametrize(
    "av_rawdata, annotations, result",
    [
        (
            {
                ("heute", "heute"): {
                    "CPU load": [
                        {
                            "site": "heute",
                            "host_name": "heute",
                            "service_description": "CPU load",
                            "duration": 31282,
                            "from": 1590530400,
                            "until": 1590561682,
                            "state": -1,
                            "host_down": 0,
                            "in_downtime": 0,
                            "in_host_downtime": 0,
                            "in_notification_period": 1,
                            "in_service_period": 1,
                            "is_flapping": 0,
                            "log_output": "OK - 15 min load: 1.78 at 8 Cores (0.22 per Core)",
                        },
                        {
                            "site": "heute",
                            "host_name": "heute",
                            "service_description": "CPU load",
                            "duration": 3285,
                            "from": 1590561682,
                            "until": 1590564967,
                            "state": 0,
                            "host_down": 0,
                            "in_downtime": 0,
                            "in_host_downtime": 0,
                            "in_notification_period": 1,
                            "in_service_period": 1,
                            "is_flapping": 0,
                            "log_output": "OK - 15 min load: 1.78 at 8 Cores (0.22 per Core)",
                        },
                    ]
                }
            },
            {
                ("heute", "heute", None): [],
                ("heute", "heute", "CPU load"): [
                    {
                        "service": "CPU load",
                        "service_state": 2,
                        "from": 1590471893.0,
                        "until": 1590496168.0,
                        "downtime": True,
                        "text": "sdfg\n",
                        "hide_from_report": False,
                        "date": 1590496182.311858,
                        "author": "cmkadmin",
                    },
                    {
                        "service": "CPU load",
                        "service_state": 0,
                        "from": 1590496168.0,
                        "until": 1590498082.0,
                        "downtime": None,
                        "text": "adgf\n",
                        "hide_from_report": False,
                        "date": 1590498137.9092221,
                        "author": "cmkadmin",
                    },
                    {
                        "service": "CPU load",
                        "from": 1590561682.0,
                        "until": 1590563170.0,
                        "downtime": True,
                        "text": "Annotation with added Downtime\n",
                        "hide_from_report": False,
                        "date": 1590563194.9577022,
                        "author": "cmkadmin",
                    },
                    {
                        "service": "CPU load",
                        "from": 1590563170.0,
                        "until": 1590563208.0,
                        "downtime": None,
                        "text": "Annotation without Downtime\n",
                        "hide_from_report": False,
                        "date": 1590563221.8145533,
                        "author": "cmkadmin",
                    },
                    {
                        "service": "CPU load",
                        "from": 1590563170.0,
                        "until": 1590563194.0,
                        "downtime": False,
                        "text": "Annottion with removed downtime\n",
                        "hide_from_report": False,
                        "date": 1590563227.5949395,
                        "author": "cmkadmin",
                    },
                ],
                ("heute", "heute", "Filesystem /snap/core18/1705"): [
                    {
                        "service": "Filesystem /snap/core18/1705",
                        "from": 1590515368.0,
                        "until": 1590515472.0,
                        "downtime": True,
                        "text": "sadf\n",
                        "hide_from_report": False,
                        "date": 1590521475.382475,
                        "author": "cmkadmin",
                    }
                ],
            },
            {
                ("heute", "heute"): {
                    "CPU load": [
                        {
                            "site": "heute",
                            "host_name": "heute",
                            "service_description": "CPU load",
                            "duration": 31282,
                            "from": 1590530400,
                            "until": 1590561682,
                            "state": -1,
                            "host_down": 0,
                            "in_downtime": 0,
                            "in_host_downtime": 0,
                            "in_notification_period": 1,
                            "in_service_period": 1,
                            "is_flapping": 0,
                            "log_output": "OK - 15 min load: 1.78 at 8 Cores (0.22 per Core)",
                        },
                        {
                            "site": "heute",
                            "host_name": "heute",
                            "service_description": "CPU load",
                            "duration": 1488.0,
                            "from": 1590561682,
                            "until": 1590563170.0,
                            "state": 0,
                            "host_down": 0,
                            "in_downtime": 1,
                            "in_host_downtime": 0,
                            "in_notification_period": 1,
                            "in_service_period": 1,
                            "is_flapping": 0,
                            "log_output": "OK - 15 min load: 1.78 at 8 Cores (0.22 per Core)",
                        },
                        {
                            "site": "heute",
                            "host_name": "heute",
                            "service_description": "CPU load",
                            "duration": 24.0,
                            "from": 1590563170.0,
                            "until": 1590563194.0,
                            "state": 0,
                            "host_down": 0,
                            "in_downtime": 0,
                            "in_host_downtime": 0,
                            "in_notification_period": 1,
                            "in_service_period": 1,
                            "is_flapping": 0,
                            "log_output": "OK - 15 min load: 1.78 at 8 Cores (0.22 per Core)",
                        },
                        {
                            "site": "heute",
                            "host_name": "heute",
                            "service_description": "CPU load",
                            "duration": 1773.0,
                            "from": 1590563194.0,
                            "until": 1590564967,
                            "state": 0,
                            "host_down": 0,
                            "in_downtime": 0,
                            "in_host_downtime": 0,
                            "in_notification_period": 1,
                            "in_service_period": 1,
                            "is_flapping": 0,
                            "log_output": "OK - 15 min load: 1.78 at 8 Cores (0.22 per Core)",
                        },
                    ]
                }
            },
        )
    ],
)
def test_reclassify_by_annotations(monkeypatch, av_rawdata, annotations, result) -> None:
    monkeypatch.setattr(availability, "load_annotations", lambda: annotations)
    assert availability.reclassify_by_annotations("service", av_rawdata) == result


@pytest.mark.parametrize(
    "annotation_from,annotation_until,result",
    [
        (40, 50, True),
        (10, 70, True),
        (10, 30, True),
        (10, 40, True),
        (40, 60, True),
        (40, 70, True),
        (10, 20, False),
        (61, 70, False),
    ],
)
def test_relevant_annotation_times(annotation_from, annotation_until, result) -> None:
    with on_time(1572253746, "CET"):
        assert (
            availability._annotation_affects_time_range(annotation_from, annotation_until, 30, 60)
            == result
        )


@pytest.mark.parametrize(
    "annotation_times,result",
    [
        (
            [
                (1543446000 + 7200, 1543446000 + 14400),
                (1543446000 + 28800, 1543446000 + 32400),
            ],
            cmk.utils.render.time_of_day,
        ),
        (
            [
                (1543446000, 1543446000),
            ],
            cmk.utils.render.time_of_day,
        ),
        ([(1543446000 - 3600, 1543446000 + 3600)], cmk.utils.render.date_and_time),
        ([(1543446000, 1543446000 + 86400)], cmk.utils.render.date_and_time),
        ([(1543446000 + 82800, 1543446000 + 172800)], cmk.utils.render.date_and_time),
    ],
)
def test_get_annotation_date_render_function(annotation_times, result) -> None:
    annotations = [((None, None, None), {"from": s, "until": e}) for s, e in annotation_times]
    with on_time(1572253746, "CET"):
        assert (
            availability.get_annotation_date_render_function(  # pylint:disable=comparison-with-callable
                annotations, {"range": ((1543446000, 1543446000 + 86399), "bla")}
            )
            == result
        )


@pytest.mark.parametrize(
    "annotations, by_host, avoptions, result",
    [
        (
            {
                ("heute", "heute", None): [],
                ("heute", "heute", "CPU load"): [
                    {
                        "service": "CPU load",
                        "service_state": 2,
                        "from": 1590471893.0,
                        "until": 1590496168.0,
                        "downtime": True,
                        "text": "sdfg\n",
                        "hide_from_report": False,
                        "date": 1590496182.311858,
                        "author": "cmkadmin",
                    },
                    {
                        "service": "CPU load",
                        "service_state": 0,
                        "from": 1590496168.0,
                        "until": 1590498082.0,
                        "downtime": None,
                        "text": "adgf\n",
                        "hide_from_report": False,
                        "date": 1590498137.9092221,
                        "author": "cmkadmin",
                    },
                ],
                ("heute", "heute", "Filesystem /snap/core18/1705"): [
                    {
                        "service": "Filesystem /snap/core18/1705",
                        "from": 1590515368.0,
                        "until": 1590515472.0,
                        "downtime": None,
                        "text": "sadf\n",
                        "hide_from_report": False,
                        "date": 1590515478.9377735,
                        "author": "cmkadmin",
                    }
                ],
            },
            {
                ("heute", "heute"): {
                    "Filesystem /snap/core18/1705": [
                        {
                            "site": "heute",
                            "host_name": "heute",
                            "service_description": "Filesystem/snap/core18/1705",
                            "duration": 27893,
                            "from": 1590444000,
                            "until": 1590471893,
                            "state": -1,
                            "host_down": 0,
                            "in_downtime": 0,
                            "in_host_downtime": 0,
                            "in_notification_period": 1,
                            "in_service_period": 1,
                            "is_flapping": 0,
                            "log_output": "No informationabout that period of time available",
                        },
                        {
                            "site": "heute",
                            "host_name": "heute",
                            "service_description": "Filesystem /snap/core18/1705",
                            "duration": 18,
                            "from": 1590471875,
                            "until": 1590471893,
                            "state": -1,
                            "host_down": 0,
                            "in_downtime": 0,
                            "in_host_downtime": 0,
                            "in_notification_period": 1,
                            "in_service_period": 1,
                            "is_flapping": 0,
                            "log_output": "",
                        },
                        {
                            "site": "heute",
                            "host_name": "heute",
                            "service_description": "Filesystem /snap/core18/1705",
                            "duration": 29093,
                            "from": 1590471893,
                            "until": 1590500986,
                            "state": 2,
                            "host_down": 0,
                            "in_downtime": 0,
                            "in_host_downtime": 0,
                            "in_notification_period": 1,
                            "in_service_period": 1,
                            "is_flapping": 0,
                            "log_output": "CRIT -100% used (55.00 of 55.00 MB), (warn/crit at 80.0%/90.0%),Inodes Used: 100% (warn/crit at 90.0%/95.0%), inodes available:0.00 /0%(!!)",
                        },
                        {
                            "site": "heute",
                            "host_name": "heute",
                            "service_description": "Filesystem /snap/core18/1705",
                            "duration": 14382,
                            "from": 1590500986,
                            "until": 1590515368,
                            "state": -1,
                            "host_down": 0,
                            "in_downtime": 0,
                            "in_host_downtime": 0,
                            "in_notification_period": 1,
                            "in_service_period": 1,
                            "is_flapping": 0,
                            "log_output": "CRIT - 100% used (55.00 of 55.00 MB), (warn/crit at80.0%/90.0%), Inodes Used: 100% (warn/crit at 90.0%/95.0%),inodes available: 0.00 /0%(!!)",
                        },
                        {
                            "site": "heute",
                            "host_name": "heute",
                            "service_description": "Filesystem /snap/core18/1705",
                            "duration": 815,
                            "from": 1590515368,
                            "until": 1590516183,
                            "state": 2,
                            "host_down": 0,
                            "in_downtime": 0,
                            "in_host_downtime": 0,
                            "in_notification_period": 1,
                            "in_service_period": 1,
                            "is_flapping": 0,
                            "log_output": "CRIT - 100% used(55.00 of 55.00 MB), (warn/crit at 80.0%/90.0%), InodesUsed: 100% (warn/crit at 90.0%/95.0%), inodesavailable: 0.00 /0%(!!)",
                        },
                    ]
                }
            },
            {
                "range": ((1590444000.0, 1590516346.364978), "Today"),
                "rangespec": "d0",
                "labelling": [],
                "av_levels": None,
                "av_filter_outages": {"warn": 0.0, "crit": 0.0, "non-ok": 0.0},
                "outage_statistics": ([], []),
                "av_mode": False,
                "service_period": "honor",
                "notification_period": "ignore",
                "grouping": None,
                "dateformat": "yyyy-mm-dd hh:mm:ss",
                "timeformat": ("perc", "percentage_2", None),
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
            [
                (
                    ("heute", "heute", "Filesystem /snap/core18/1705"),
                    {
                        "service": "Filesystem /snap/core18/1705",
                        "from": 1590515368.0,
                        "until": 1590515472.0,
                        "downtime": None,
                        "text": "sadf\n",
                        "hide_from_report": False,
                        "date": 1590515478.9377735,
                        "author": "cmkadmin",
                    },
                )
            ],
        )
    ],
)
def test_get_relevant_annotations(annotations, by_host, avoptions, result) -> None:
    assert (
        availability.get_relevant_annotations(annotations, by_host, "service", avoptions) == result
    )
