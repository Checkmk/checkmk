#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import Counter

import pytest

from tests.testlib import Check

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State

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


def test_inotify_parse() -> None:
    assert Section(*PARSED) == parse_inotify(INFO)


def test_discovery() -> None:
    assert sorted(discover_inotify(Section(*PARSED))) == [
        Service(item="File /tmp/noti/nodata"),
        Service(item="File /tmp/noti/test"),
        Service(item="Folder /tmp/noti"),
    ]


def test_updated_data() -> None:
    item = "Folder /tmp/noti"
    params = {
        "age_last_operation": [
            ("modify", 90, 110),
            ("open", 80, 90),
            ("just_for_test_coverage", 1, 2),
        ]
    }
    section = Section(*PARSED)
    last_status: dict = {}
    now = 1465470156

    assert list(check_inotify(item, params, section, last_status, now)) == [
        Result(state=State.OK, summary="Time since last delete: 1 minute 38 seconds"),
        Result(
            state=State.WARN,
            summary="Time since last modify: 1 minute 40 seconds (warn/crit at 1 minute 30 seconds/1 minute 50 seconds)",
        ),
        Result(
            state=State.CRIT,
            summary="Time since last open: 1 minute 40 seconds (warn/crit at 1 minute 20 seconds/1 minute 30 seconds)",
        ),
        Result(state=State.UNKNOWN, summary="Time since last just_for_test_coverage: unknown"),
        Result(state=State.WARN, summary="Incomplete data!"),
        Result(state=State.WARN, summary="1 warning(s): I assume a warning looks like this!"),
    ]
    assert last_status == {
        "delete": 1465470058,
        "modify": 1465470056,
        "open": 1465470056,
    }


def test_not_configured() -> None:
    item = "File /tmp/noti/nodata"
    params = {"age_last_operation": [("modify", 90, 110)]}
    section = Section(Counter(), {}, {})
    last_status: dict = {}
    now = 1465470156

    assert not list(check_inotify(item, params, section, last_status, now))
    assert not last_status


def test_nodata() -> None:
    item = "File /tmp/noti/nodata"
    params = {"age_last_operation": [("modify", 90, 110)]}
    section = Section(Counter(), {"/tmp/noti/nodata": "file"}, {})
    last_status: dict = {}
    now = 1465470156

    assert list(check_inotify(item, params, section, last_status, now)) == [
        Result(state=State.UNKNOWN, summary="Time since last modify: unknown"),
        Result(state=State.OK, summary="No data available yet"),
    ]
    assert not last_status


def test_old_status() -> None:
    item = "File /tmp/noti/nodata"
    params = {"age_last_operation": [("modify", 90, 110)]}
    section = Section(Counter(), {"/tmp/noti/nodata": "file"}, {})
    last_status = {"modify": 1465470000}
    now = 1465470156

    assert list(check_inotify(item, params, section, last_status, now)) == [
        Result(
            state=State.CRIT,
            summary="Time since last modify: 2 minutes 36 seconds (warn/crit at 1 minute 30 seconds/1 minute 50 seconds)",
        ),
    ]
    assert last_status == {"modify": 1465470000}
