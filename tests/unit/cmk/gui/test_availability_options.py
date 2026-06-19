#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.availability.options import get_default_avoptions


def test_get_default_avoptions(request_context: None) -> None:
    """Lock the option defaults derived from the valuespecs.

    get_default_avoptions() derives its values from the ``default_value=`` of
    the option valuespecs (get_av_display_options()/get_av_computation_options())
    so there is a single source of truth. This pins the resulting defaults so an
    unintended change to a valuespec default (or to the derivation) is caught.
    """
    assert get_default_avoptions((0.0, 60.0)) == {
        "range": ((0.0, 60.0), ""),
        "rangespec": "d0",
        "labelling": [],
        "av_levels": None,
        "outage_statistics": ([], []),
        "timeformat": ("perc", "percentage_2", None),
        "av_mode": False,
        "grouping": None,
        "dateformat": "yyyy-mm-dd hh:mm:ss",
        "summary": "sum",
        "show_timeline": False,
        "downtimes": {"include": "honor", "exclude_ok": False},
        "consider": {"flapping": True, "host_down": True, "unmonitored": True},
        "state_grouping": {"warn": "warn", "unknown": "unknown", "host_down": "host_down"},
        "av_filter_outages": {"warn": 0.0, "crit": 0.0, "non-ok": 0.0},
        "host_state_grouping": {"unreach": "unreach"},
        "service_period": "honor",
        "notification_period": "ignore",
        "short_intervals": 0,
        "dont_merge": False,
        "timelimit": 30,
        "logrow_limit": 5000,
    }
