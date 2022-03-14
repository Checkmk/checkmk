import pytest

from cmk.gui.availability import layout_availability_table


@pytest.mark.parametrize(
    "what, group_title, availability_table, avoptions, result",
    [
        (
            "service",
            None,
            [
                {
                    "site": "heute",
                    "host": "heute",
                    "alias": "heute",
                    "service": "CPU load",
                    "display_name": "CPU load",
                    "states": {"ok": 39399},
                    "considered_duration": 39399,
                    "total_duration": 39399,
                    "statistics": {},
                    "groups": None,
                    "timeline": [
                        (
                            {
                                "site": "heute",
                                "host_name": "heute",
                                "service_description": "CPU load",
                                "duration": 39399,
                                "from": 1618351200,
                                "until": 1618390599,
                                "state": 0,
                                "host_down": 0,
                                "in_downtime": 0,
                                "in_host_downtime": 0,
                                "in_notification_period": 1,
                                "in_service_period": 1,
                                "is_flapping": 0,
                                "log_output": "15 min load: 1.60, 15 min load per core: 0.20 (8 cores)",
                            },
                            "ok",
                        )
                    ],
                },
                {
                    "site": "heute",
                    "host": "heute",
                    "alias": "heute",
                    "service": "CPU utilization",
                    "display_name": "CPU utilization",
                    "states": {"ok": 39399},
                    "considered_duration": 39399,
                    "total_duration": 39399,
                    "statistics": {},
                    "groups": None,
                    "timeline": [
                        (
                            {
                                "site": "heute",
                                "host_name": "heute",
                                "service_description": "CPU utilization",
                                "duration": 39399,
                                "from": 1618351200,
                                "until": 1618390599,
                                "state": 0,
                                "host_down": 0,
                                "in_downtime": 0,
                                "in_host_downtime": 0,
                                "in_notification_period": 1,
                                "in_service_period": 1,
                                "is_flapping": 0,
                                "log_output": "Total CPU: 24.43%",
                            },
                            "ok",
                        )
                    ],
                },
                {
                    "site": "heute",
                    "host": "heute",
                    "alias": "heute",
                    "service": "Filesystem /opt/omd/sites/stable/tmp",
                    "display_name": "Filesystem /opt/omd/sites/stable/tmp",
                    "states": {"ok": 39399},
                    "considered_duration": 39399,
                    "total_duration": 39399,
                    "statistics": {},
                    "groups": None,
                    "timeline": [
                        (
                            {
                                "site": "heute",
                                "host_name": "heute",
                                "service_description": "Filesystem /opt/omd/sites/stable/tmp",
                                "duration": 39399,
                                "from": 1618351200,
                                "until": 1618390599,
                                "state": 0,
                                "host_down": 0,
                                "in_downtime": 0,
                                "in_host_downtime": 0,
                                "in_notification_period": 1,
                                "in_service_period": 1,
                                "is_flapping": 0,
                                "log_output": "0.07% used (5.71 MB of 7.76 GB)",
                            },
                            "ok",
                        )
                    ],
                },
            ],
            {
                "labelling": ["omit_buttons"],
                "av_levels": (99.0, 95.0),
                "outage_statistics": ([], []),
                "timeformat": ("perc", "percentage_0", "hhmmss"),
                "av_mode": True,
                "grouping": None,
                "dateformat": "yyyy-mm-dd hh:mm:ss",
                "summary": "sum",
                "show_timeline": False,
                "elements": ["table"],
                "timelimit": 300,
                "range": ((1618351200.0, 1618390599.6352015), "Today"),
                "rangespec": "d0",
                "av_filter_outages": {"warn": 0.0, "crit": 0.0, "non-ok": 0.0},
                "service_period": "honor",
                "notification_period": "ignore",
                "short_intervals": 0,
                "dont_merge": False,
                "logrow_limit": 5000,
                "downtimes": {"include": "honor", "exclude_ok": False},
                "consider": {"flapping": True, "host_down": True, "unmonitored": True},
                "host_state_grouping": {"unreach": "unreach"},
                "state_grouping": {"warn": "warn", "unknown": "unknown", "host_down": "host_down"},
            },
            {
                "title": None,
                "rows": [
                    {"urls": [], "object": 0, "cells": [("100%", "state0 state narrow number")]},
                    {"urls": [], "object": 0, "cells": [("100%", "state0 state narrow number")]},
                    {"urls": [], "object": 0, "cells": [("100%", "state0 state narrow number")]},
                ],
                "object_titles": ["Host", "Service"],
                "cell_titles": [("Avail.", None)],
                "summary": [("100%", "state0 state narrow number")],
            },
        )
    ],
)
def test_availability_percentage_only_option(
    monkeypatch, what, group_title, availability_table, avoptions, result
):
    monkeypatch.setattr("cmk.gui.availability.get_object_cells", lambda what, av, lab: 0)
    assert layout_availability_table(what, group_title, availability_table, avoptions) == result


@pytest.mark.parametrize(
    "what, group_title, availability_table, avoptions, result",
    [
        (
            "service",
            None,
            [
                {
                    "site": "heute",
                    "host": "heute",
                    "alias": "heute",
                    "service": "CPU load",
                    "display_name": "CPU load",
                    "states": {"ok": 39399},
                    "considered_duration": 39399,
                    "total_duration": 39399,
                    "statistics": {},
                    "groups": None,
                    "timeline": [
                        (
                            {
                                "site": "heute",
                                "host_name": "heute",
                                "service_description": "CPU load",
                                "duration": 39399,
                                "from": 1618351200,
                                "until": 1618390599,
                                "state": 0,
                                "host_down": 0,
                                "in_downtime": 0,
                                "in_host_downtime": 0,
                                "in_notification_period": 1,
                                "in_service_period": 1,
                                "is_flapping": 0,
                                "log_output": "15 min load: 1.60, 15 min load per core: 0.20 (8 cores)",
                            },
                            "ok",
                        )
                    ],
                },
                {
                    "site": "heute",
                    "host": "heute",
                    "alias": "heute",
                    "service": "CPU utilization",
                    "display_name": "CPU utilization",
                    "states": {"ok": 39399},
                    "considered_duration": 39399,
                    "total_duration": 39399,
                    "statistics": {},
                    "groups": None,
                    "timeline": [
                        (
                            {
                                "site": "heute",
                                "host_name": "heute",
                                "service_description": "CPU utilization",
                                "duration": 39399,
                                "from": 1618351200,
                                "until": 1618390599,
                                "state": 0,
                                "host_down": 0,
                                "in_downtime": 0,
                                "in_host_downtime": 0,
                                "in_notification_period": 1,
                                "in_service_period": 1,
                                "is_flapping": 0,
                                "log_output": "Total CPU: 24.43%",
                            },
                            "ok",
                        )
                    ],
                },
                {
                    "site": "heute",
                    "host": "heute",
                    "alias": "heute",
                    "service": "Filesystem /opt/omd/sites/stable/tmp",
                    "display_name": "Filesystem /opt/omd/sites/stable/tmp",
                    "states": {"ok": 39399},
                    "considered_duration": 39399,
                    "total_duration": 39399,
                    "statistics": {},
                    "groups": None,
                    "timeline": [
                        (
                            {
                                "site": "heute",
                                "host_name": "heute",
                                "service_description": "Filesystem /opt/omd/sites/stable/tmp",
                                "duration": 39399,
                                "from": 1618351200,
                                "until": 1618390599,
                                "state": 0,
                                "host_down": 0,
                                "in_downtime": 0,
                                "in_host_downtime": 0,
                                "in_notification_period": 1,
                                "in_service_period": 1,
                                "is_flapping": 0,
                                "log_output": "0.07% used (5.71 MB of 7.76 GB)",
                            },
                            "ok",
                        )
                    ],
                },
            ],
            {
                "labelling": ["omit_buttons"],
                "av_levels": (99.0, 95.0),
                "outage_statistics": ([], []),
                "timeformat": ("time", "percentage_0", "hhmmss"),
                "av_mode": True,
                "grouping": None,
                "dateformat": "yyyy-mm-dd hh:mm:ss",
                "summary": "sum",
                "show_timeline": False,
                "elements": ["table"],
                "timel    imit": 300,
                "range": ((1618351200.0, 1618394469.278563), "Today"),
                "rangespec": "d0",
                "av_filter_outages": {"warn": 0.0, "crit": 0.0, "non-ok": 0.0},
                "service_period": "honor",
                "notification_period": "ignore",
                "short_intervals": 0,
                "dont_merge": False,
                "logrow_limit": 5000,
                "downtimes": {"include": "honor", "excl    ude_ok": False},
                "consider": {"flapping": True, "host_down": True, "unmonitored": True},
                "host_state_grouping": {"unreach": "unreach"},
                "state_grouping": {"warn": "warn", "unknown": "unknown", "host_down": "host_down"},
            },
            {
                "title": None,
                "rows": [
                    {
                        "cells": [("10:56:39", "state0 state narrow number")],
                        "object": 0,
                        "urls": [],
                    },
                    {
                        "cells": [("10:56:39", "state0 state narrow number")],
                        "object": 0,
                        "urls": [],
                    },
                    {
                        "cells": [("10:56:39", "state0 state narrow number")],
                        "object": 0,
                        "urls": [],
                    },
                ],
                "object_titles": ["Host", "Service"],
                "cell_titles": [("Avail.", None)],
                "summary": [("32:49:57", "state0 state narrow number")],
            },
        )
    ],
)
def test_availability_time_only_option(
    monkeypatch, what, group_title, availability_table, avoptions, result
):
    monkeypatch.setattr("cmk.gui.availability.get_object_cells", lambda what, av, lab: 0)
    assert layout_availability_table(what, group_title, availability_table, avoptions) == result
