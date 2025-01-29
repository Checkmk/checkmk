#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import Counter

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.collection.agent_based.inotify import _check_inotify as check_inotify
from cmk.plugins.collection.agent_based.inotify import discover_inotify, parse_inotify, Section

Params = dict[str, list[tuple[str, float, float]]]

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

_SECTION = Section(
    Counter({"I assume a warning looks like this!": 1}),
    {
        "/tmp/noti/nodata": "file",
        "/tmp/noti/test": "file",
        "/tmp/noti": "folder",
    },
    {
        "/tmp/noti": {
            "modify": 1465470056,
            "open": 1465470056,
            "delete": 1465470058,
        },
        "/tmp/noti/test": {
            "modify": 1465470056,
            "open": 1465470056,
            "delete": 1465470058,
        },
    },
)


def test_inotify_parse() -> None:
    assert _SECTION == parse_inotify(INFO)


def test_discovery() -> None:
    assert sorted(discover_inotify(_SECTION)) == [
        Service(item="File /tmp/noti/nodata"),
        Service(item="File /tmp/noti/test"),
        Service(item="Folder /tmp/noti"),
    ]


def test_updated_data() -> None:
    item = "Folder /tmp/noti"
    params: Params = {
        "age_last_operation": [
            ("modify", 90, 110),
            ("open", 80, 90),
            ("just_for_test_coverage", 1, 2),
        ]
    }
    last_status: dict = {}
    now = 1465470156

    assert list(check_inotify(item, params, _SECTION, last_status, now)) == [
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
    params: Params = {"age_last_operation": [("modify", 90, 110)]}
    section = Section(Counter(), {}, {})
    last_status: dict = {}
    now = 1465470156

    assert not list(check_inotify(item, params, section, last_status, now))
    assert not last_status


def test_nodata() -> None:
    item = "File /tmp/noti/nodata"
    params: Params = {"age_last_operation": [("modify", 90, 110)]}
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
    params: Params = {"age_last_operation": [("modify", 90, 110)]}
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
