#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import Counter
from typing import Dict

import pytest  # type: ignore[import]

from tests.testlib import Check  # type: ignore[import]

pytestmark = pytest.mark.checks

INFO = [
    ["warning:", "I assume a warning looks like this!"],
    ["configured", "folder", "/tmp/noti"],
    ["configured", "file", "/tmp/noti/test"],
    ["configured", "file", "/tmp/noti/nodata"],
    ["1465470055", "modify", "/tmp/noti/test", "5", "1465470055"],
    ["1465470055", "open", "/tmp/noti/test", "5", "1465470055"],
    ["1465470055", "modify", "/tmp/noti/test", "5", "1465470055"],
    ["1465470056", "modify", "/tmp/noti/test", "5", "1465470056"],
    ["1465470056", "open", "/tmp/noti/test", "5", "1465470056"],
    ["1465470058", "delete", "/tmp/noti/test"],
]

PARSED = (
    # warnings
    Counter({"I assume a warning looks like this!": 1}),
    # configured:
    {
        "/tmp/noti/nodata": "file",
        "/tmp/noti/test": "file",
        "/tmp/noti": "folder",
    },
    # stats
    {
        "/tmp/noti": {
            "modify": 1465470056,
            "open": 1465470056,
            "delete": 1465470058,
        },
        "/tmp/noti/test": {"modify": 1465470056, "open": 1465470056, "delete": 1465470058},
    },
)


def Section(*a, **kw):
    return Check("inotify").context["Section"](*a, **kw)


def parse_inotify(*a, **kw):
    return Check("inotify").context["parse_inotify"](*a, **kw)


def discover_inotify(*a, **kw):
    return Check("inotify").context["discover_inotify"](*a, **kw)


def check_inotify(*a, **kw):
    return Check("inotify").context["_check_inotify"](*a, **kw)


def test_inotify_parse():
    assert Section(*PARSED) == parse_inotify(INFO)


def test_discovery():
    assert sorted(discover_inotify(Section(*PARSED))) == [
        ("File /tmp/noti/nodata", {}),
        ("File /tmp/noti/test", {}),
        ("Folder /tmp/noti", {}),
    ]


def test_updated_data():
    item = "Folder /tmp/noti"
    params = {
        "age_last_operation": [
            ("modify", 90, 110),
            ("open", 80, 90),
            ("just_for_test_coverage", 1, 2),
        ]
    }
    section = Section(*PARSED)
    last_status: Dict = {}
    now = 1465470156

    assert list(check_inotify(item, params, section, last_status, now)) == [
        (0, "Time since last delete: 98 s", []),
        (1, "Time since last modify: 100 s (warn/crit at 90 s/110 s)", []),
        (2, "Time since last open: 100 s (warn/crit at 80 s/90 s)", []),
        (3, "Time since last just_for_test_coverage: unknown"),
        (1, "Incomplete data!"),
        (1, "1 warning(s): I assume a warning looks like this!"),
    ]
    assert last_status == {
        "delete": 1465470058,
        "modify": 1465470056,
        "open": 1465470056,
    }


def test_not_configured():
    item = "File /tmp/noti/nodata"
    params = {"age_last_operation": [("modify", 90, 110)]}
    section = Section(Counter(), {}, {})
    last_status: Dict = {}
    now = 1465470156

    assert not list(check_inotify(item, params, section, last_status, now))
    assert not last_status


def test_nodata():
    item = "File /tmp/noti/nodata"
    params = {"age_last_operation": [("modify", 90, 110)]}
    section = Section(Counter(), {"/tmp/noti/nodata": "file"}, {})
    last_status: Dict = {}
    now = 1465470156

    assert list(check_inotify(item, params, section, last_status, now)) == [
        (3, "Time since last modify: unknown"),
        (0, "No data available yet"),
    ]
    assert not last_status


def test_old_status():
    item = "File /tmp/noti/nodata"
    params = {"age_last_operation": [("modify", 90, 110)]}
    section = Section(Counter(), {"/tmp/noti/nodata": "file"}, {})
    last_status = {"modify": 1465470000}
    now = 1465470156

    assert list(check_inotify(item, params, section, last_status, now)) == [
        (2, "Time since last modify: 156 s (warn/crit at 90 s/110 s)", []),
    ]
    assert last_status == {"modify": 1465470000}
