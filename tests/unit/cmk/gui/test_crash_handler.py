#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.crash import make_crash_report_base_path, VersionInfo
from cmk.gui.crash_handler import (
    GUICrashReport,
    JavascriptCrashReport,
    JavascriptDetails,
    RequestDetails,
)


def test_gui_crash_report_from_exception_without_request_context(tmp_path: Path) -> None:
    try:
        raise ValueError("Test")
    except ValueError:
        report = GUICrashReport.from_exception(
            version_info=VersionInfo(
                core="test",
                python_version="test",
                edition="test",
                python_paths=["foo", "bar"],
                version="3.99",
                time=0.0,
                os="Foobuntu",
            ),
            crash_report_base_path=make_crash_report_base_path(tmp_path),
        )
        # In this case we currently don't produce unknown request details
        assert report.crash_info["details"] == RequestDetails(
            page="unknown",
            vars={},
            username=None,
            user_agent="unknown",
            referer="unknown",
            is_mobile=False,
            is_ssl_request=False,
            language="unknown",
            request_method="unknown",
        )


def test_gui_crash_report_strips_html_from_exc_value(tmp_path: Path) -> None:
    try:
        raise ValueError(
            "Error running automation call <tt>bake-agents</tt> (exit code 2), error: "
            "<pre>[ERROR] failed\nTraceback (most recent call last):\n  boom</pre>"
        )
    except ValueError:
        report = GUICrashReport.from_exception(
            version_info=VersionInfo(
                core="test",
                python_version="test",
                edition="test",
                python_paths=["foo", "bar"],
                version="3.99",
                time=0.0,
                os="Foobuntu",
            ),
            crash_report_base_path=make_crash_report_base_path(tmp_path),
        )
    exc_value = report.crash_info["exc_value"]
    assert "<" not in exc_value
    assert exc_value.startswith(
        "Error running automation call bake-agents (exit code 2), error: [ERROR] failed"
    )


@pytest.mark.usefixtures("request_context")
def test_gui_crash_report_from_exception_with_request_context(tmp_path: Path) -> None:
    try:
        raise ValueError("Test")
    except ValueError:
        report = GUICrashReport.from_exception(
            version_info=VersionInfo(
                core="test",
                python_version="test",
                edition="test",
                python_paths=["foo", "bar"],
                version="3.99",
                time=0.0,
                os="Foobuntu",
            ),
            crash_report_base_path=make_crash_report_base_path(tmp_path),
        )
        details = report.crash_info["details"]
        assert details["page"] == "index.py"


_VERSION_INFO = VersionInfo(
    core="test",
    python_version="test",
    edition="test",
    python_paths=["foo", "bar"],
    version="3.99",
    time=0.0,
    os="Foobuntu",
)

_JAVASCRIPT_DETAILS = JavascriptDetails(
    url="http://localhost/heute/check_mk/dashboard.py",
    component="DashboardApp",
    user_agent="Mozilla/5.0",
    username="cmkadmin",
    language="en",
    context="",
)


@pytest.mark.parametrize(
    "stack, expected",
    [
        pytest.param(
            "TypeError: cannot read x\n"
            "    at renderTile (http://localhost/heute/check_mk/js/main.js:120:31)\n"
            "    at http://localhost/heute/check_mk/js/main.js:8:1\n",
            [
                (
                    "http://localhost/heute/check_mk/js/main.js",
                    120,
                    "renderTile",
                    "at renderTile (http://localhost/heute/check_mk/js/main.js:120:31)",
                ),
                (
                    "http://localhost/heute/check_mk/js/main.js",
                    8,
                    "<anonymous>",
                    "at http://localhost/heute/check_mk/js/main.js:8:1",
                ),
            ],
            id="v8-drops-message-line-and-keeps-named-and-anonymous-frames",
        ),
        pytest.param(
            "renderTile@http://localhost/heute/check_mk/js/main.js:120:31\n"
            "@http://localhost/heute/check_mk/js/main.js:8:1\n",
            [
                (
                    "http://localhost/heute/check_mk/js/main.js",
                    120,
                    "renderTile",
                    "renderTile@http://localhost/heute/check_mk/js/main.js:120:31",
                ),
                (
                    "http://localhost/heute/check_mk/js/main.js",
                    8,
                    "<anonymous>",
                    "@http://localhost/heute/check_mk/js/main.js:8:1",
                ),
            ],
            id="spidermonkey-frames",
        ),
        pytest.param(
            "    at renderTile (http://localhost:5173/src/main.ts:120:31)\n",
            [
                (
                    "http://localhost:5173/src/main.ts",
                    120,
                    "renderTile",
                    "at renderTile (http://localhost:5173/src/main.ts:120:31)",
                )
            ],
            id="port-in-url-is-not-mistaken-for-the-line-number",
        ),
        pytest.param(
            "    at renderTile (foo.js:120)\n",
            [("foo.js", 120, "renderTile", "at renderTile (foo.js:120)")],
            id="frame-without-column",
        ),
        pytest.param(
            "    at Object.<anonymous> (<anonymous>)\n    at eval (eval at foo)\n",
            [],
            id="frames-without-source-location-are-dropped",
        ),
        pytest.param("", [], id="empty-stack"),
    ],
)
def test_javascript_crash_report_parse_stack(
    stack: str, expected: list[tuple[str, int, str, str]]
) -> None:
    assert list(JavascriptCrashReport.parse_stack(stack)) == expected


def test_javascript_crash_report_from_browser_error(tmp_path: Path) -> None:
    report = JavascriptCrashReport.from_browser_error(
        version_info=_VERSION_INFO,
        error_name="TypeError",
        error_message="cannot read x",
        stack="    at renderTile (http://localhost/heute/check_mk/js/main.js:120:31)",
        details=_JAVASCRIPT_DETAILS,
        crash_report_base_path=make_crash_report_base_path(tmp_path),
    )

    assert report.crash_info["crash_type"] == "javascript"
    assert report.crash_info["exc_type"] == "TypeError"
    assert report.crash_info["exc_value"] == "cannot read x"
    assert report.crash_info["exc_traceback"] == [
        (
            "http://localhost/heute/check_mk/js/main.js",
            120,
            "renderTile",
            "at renderTile (http://localhost/heute/check_mk/js/main.js:120:31)",
        )
    ]
    assert report.crash_info["details"] == _JAVASCRIPT_DETAILS
    assert report.crash_dir().parent.name == "javascript"


def test_javascript_crash_report_never_records_python_local_vars(tmp_path: Path) -> None:
    secret = "s3cret"  # noqa: F841
    try:
        raise ValueError("unrelated server side error")
    except ValueError:
        report = JavascriptCrashReport.from_browser_error(
            version_info=_VERSION_INFO,
            error_name="TypeError",
            error_message="cannot read x",
            stack="",
            details=_JAVASCRIPT_DETAILS,
            crash_report_base_path=make_crash_report_base_path(tmp_path),
        )

    assert report.crash_info["local_vars"] == ""
    assert report.crash_info["exc_type"] == "TypeError"


def test_javascript_crash_report_strips_html_from_exception_fields(tmp_path: Path) -> None:
    report = JavascriptCrashReport.from_browser_error(
        version_info=_VERSION_INFO,
        error_name="<b>TypeError</b>",
        error_message="cannot read <script>alert(1)</script>",
        stack="",
        details=_JAVASCRIPT_DETAILS,
        crash_report_base_path=make_crash_report_base_path(tmp_path),
    )

    assert report.crash_info["exc_type"] == "TypeError"
    assert "<" not in report.crash_info["exc_value"]
