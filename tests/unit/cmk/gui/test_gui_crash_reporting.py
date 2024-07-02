#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.crash_reporting import crash_report_registry

from cmk.gui.crash_handler import GUICrashReport


def test_gui_crash_report_registry() -> None:
    assert crash_report_registry["gui"] == GUICrashReport
