#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.gui.crash_reporting.views import CrashReportsRowTable


def _raw_crash_row(crash_id: str, time: object) -> dict[str, str]:
    return {
        "site": "heute",
        "crash_id": crash_id,
        "crash_type": "gui",
        "crash_info": json.dumps(
            {
                "time": time,
                "version": "2.4.0p9",
                "exc_type": "ValueError",
                "exc_value": "boom",
                "exc_traceback": [],
            }
        ),
    }


def test_parse_rows_skips_crash_report_with_unreadable_time() -> None:
    # A crash report whose time field is not a number must not take the other
    # reports (and with them the whole crash report view) down with it.
    rows = list(
        CrashReportsRowTable().parse_rows(
            [
                _raw_crash_row("readable", 1734000000.0),
                _raw_crash_row("unreadable", "1734000000"),
            ]
        )
    )

    assert [row["crash_id"] for row in rows] == ["readable"]
