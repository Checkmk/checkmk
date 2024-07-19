#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils import paths

from cmk.gui.crash_handler import GUICrashReport

from cmk.ccc.crash_reporting import crash_report_registry


def test_gui_crash_report_registry() -> None:
    assert crash_report_registry["gui"] == GUICrashReport


def test_gui_crash_report_from_exception_without_request_context() -> None:
    try:
        raise ValueError("Test")
    except ValueError:
        report = GUICrashReport.from_exception(paths.crash_dir, {})
        # In this case we currently don't produce any type specific details
        assert not report.crash_info["details"]


@pytest.mark.usefixtures("request_context")
def test_gui_crash_report_from_exception_with_request_context() -> None:
    try:
        raise ValueError("Test")
    except ValueError:
        report = GUICrashReport.from_exception(paths.crash_dir, {})
        assert report.crash_info["details"]["page"] == "index.py"
