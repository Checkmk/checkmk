#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.crash_reporting import crash_report_registry
from cmk.gui.crash_handler import GUICrashReport, RequestDetails
from cmk.utils import paths


def test_gui_crash_report_registry() -> None:
    assert crash_report_registry["gui"] == GUICrashReport


def test_gui_crash_report_from_exception_without_request_context() -> None:
    try:
        raise ValueError("Test")
    except ValueError:
        report = GUICrashReport.from_exception(
            paths.crash_dir,
            {
                "core": "test",
                "python_version": "test",
                "edition": "test",
                "python_paths": ["foo", "bar"],
                "version": "3.99",
                "time": 0.0,
                "os": "Foobuntu",
            },
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


@pytest.mark.usefixtures("request_context")
def test_gui_crash_report_from_exception_with_request_context() -> None:
    try:
        raise ValueError("Test")
    except ValueError:
        report = GUICrashReport.from_exception(
            paths.crash_dir,
            {
                "core": "test",
                "python_version": "test",
                "edition": "test",
                "python_paths": ["foo", "bar"],
                "version": "3.99",
                "time": 0.0,
                "os": "Foobuntu",
            },
        )
        details = report.crash_info["details"]
        assert details["page"] == "index.py"
