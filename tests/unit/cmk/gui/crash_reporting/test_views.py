#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.gui.crash_reporting.views import (
    check_crash_source,
    cmp_crash_source,
    crash_exception_row_filter,
    CrashReportsRowTable,
    PainterCrashException,
)
from cmk.gui.logged_in import LoggedInNobody, LoggedInSuperUser, LoggedInUser
from cmk.gui.painter import Cell
from cmk.gui.type_defs import Row
from cmk.gui.utils.roles import UserPermissions
from cmk.livestatus_client.testing import MockLiveStatusConnection

BUILT_IN_FILE = "/omd/sites/heute/lib/python3/cmk/base/modes/check_mk.py"
LOCAL_FILE = "/omd/sites/heute/local/lib/python3/cmk_addons/plugins/acme/agent_based/acme.py"
OTHER_LOCAL_FILE = "/omd/sites/heute/local/lib/python3/cmk_addons/plugins/zeta/agent_based/z.py"


def _traceback_row(*filepaths: str) -> Row:
    return {"crash_exc_traceback": [(path, 1, "parse", "return int(line)") for path in filepaths]}


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


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize(
    "user, may_see_exception",
    [
        pytest.param(LoggedInSuperUser(), True, id="permitted"),
        pytest.param(LoggedInNobody(), False, id="not permitted"),
    ],
)
def test_painter_crash_exception_render(user: LoggedInUser, may_see_exception: bool) -> None:
    cell = Cell(None, None, None, UserPermissions({}, {}, {}, []), None)
    _css, content = PainterCrashException().render(
        {"crash_exc_type": "ValueError", "crash_exc_value": "secret boom"},
        cell,
        user,
        cell.painter_context(),
    )

    assert ("secret boom" in str(content)) is may_see_exception


@pytest.mark.parametrize(
    "selection, filepath, expected",
    [
        pytest.param("built_in", BUILT_IN_FILE, True, id="built-in keeps built-in crash"),
        pytest.param("built_in", LOCAL_FILE, False, id="built-in drops extension crash"),
        pytest.param("extension", BUILT_IN_FILE, False, id="extension drops built-in crash"),
        pytest.param("extension", LOCAL_FILE, True, id="extension keeps extension crash"),
        pytest.param("ignore", BUILT_IN_FILE, True, id="ignore keeps built-in crash"),
        pytest.param("ignore", LOCAL_FILE, True, id="ignore keeps extension crash"),
    ],
)
def test_check_crash_source(selection: str, filepath: str, expected: bool) -> None:
    assert check_crash_source(selection, _traceback_row(BUILT_IN_FILE, filepath)) is expected


@pytest.mark.parametrize(
    "filtertext, expected",
    [
        pytest.param("valueerror: invalid", True, id="match across type and value"),
        pytest.param("literal", True, id="match in value"),
        pytest.param("keyerror", False, id="no match"),
        pytest.param("", True, id="empty filter"),
    ],
)
def test_crash_exception_row_filter(filtertext: str, expected: bool) -> None:
    keep = crash_exception_row_filter(filtertext, "crash_exception")

    assert keep({"crash_exc_type": "ValueError", "crash_exc_value": "invalid literal"}) is expected


def test_cmp_crash_source_sorts_built_in_before_extension() -> None:
    built_in = _traceback_row(BUILT_IN_FILE)
    extension = _traceback_row(BUILT_IN_FILE, LOCAL_FILE)

    assert cmp_crash_source("crash_exc_traceback", built_in, extension) < 0
    assert cmp_crash_source("crash_exc_traceback", extension, built_in) > 0


def test_cmp_crash_source_treats_extension_crashes_as_equal() -> None:
    assert (
        cmp_crash_source(
            "crash_exc_traceback", _traceback_row(LOCAL_FILE), _traceback_row(OTHER_LOCAL_FILE)
        )
        == 0
    )
