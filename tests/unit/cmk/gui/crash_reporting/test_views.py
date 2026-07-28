#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.gui.crash_reporting.views import CrashReportsRowTable, PainterCrashException
from cmk.livestatus_client.testing import MockLiveStatusConnection


@pytest.mark.parametrize(
    "exc_type, exc_value, expected",
    [
        pytest.param(
            "ValueError",
            "invalid literal",
            "ValueError: invalid literal",
            id="plain single line",
        ),
        pytest.param(
            "MKAutomationException",
            "Error running automation call <tt>bake-agents</tt> (exit code 2), error: "
            "<pre>[ERROR] Execution of automation 'bake-agents' failed\n"
            "Traceback (most recent call last):\n"
            '  File "automations.py", line 116, in _execute\n'
            "OSError: [Errno 2] No such file or directory</pre>",
            "MKAutomationException: Error running automation call bake-agents (exit code 2), "
            "error: [ERROR] Execution of automation 'bake-agents' failed",
            id="html markup and multi-line traceback collapse to first line",
        ),
        pytest.param(
            "RuntimeError",
            "\n\n  boom  \n\nsecond line",
            "RuntimeError: boom",
            id="leading blank lines skipped and trimmed",
        ),
        pytest.param(
            "RuntimeError",
            "",
            "RuntimeError: ",
            id="empty value",
        ),
    ],
)
def test_painter_crash_exception_summarize(exc_type: str, exc_value: str, expected: str) -> None:
    summary = PainterCrashException.summarize(exc_type, exc_value)
    assert summary == expected
    assert "\n" not in summary
    assert "<" not in summary


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


@pytest.mark.usefixtures("request_context")
def test_get_crash_report_rows_queries(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    crash_info = json.dumps({"crash_type": "gui", "crash_id": "abc-123"}).encode()
    mock_livestatus.add_table(
        "crashreports",
        [
            {
                "id": "abc-123",
                "component": "gui",
                "file:crash_info:gui/abc-123/crash.info": crash_info,
            }
        ],
    )
    with mock_livestatus(expect_status_query=True) as live:
        live.expect_query("GET crashreports\nColumns: id component")
        live.expect_query(
            "GET crashreports\n"
            "Columns: file:crash_info:gui/abc-123/crash.info\n"
            "Filter: id = abc-123\n"
            "ColumnHeaders: off"
        )
        rows = list(
            CrashReportsRowTable().get_crash_report_rows(only_sites=None, filter_headers="")
        )
    assert rows == [
        {
            "site": "NO_SITE",
            "crash_id": "abc-123",
            "crash_type": "gui",
            "crash_info": crash_info,
        }
    ]
