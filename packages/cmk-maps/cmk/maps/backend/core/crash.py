#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checkmk crash reports for the Maps daemon.

Unhandled request exceptions are persisted through the regular Checkmk crash
report store (``var/check_mk/crashes/maps/``), so they appear on the site's
crash reports page and can be submitted like any other component's crashes.
"""

from __future__ import annotations

from pathlib import Path
from typing import override

import cmk.ccc.version_info as cmk_version_info
from cmk.crash import ABCCrashReport, CrashReportStore, make_crash_report_base_path


class MapsCrashReport(ABCCrashReport[None]):
    @override
    @classmethod
    def type(cls) -> str:
        return "maps"


def create_crash_report(omd_root: Path) -> str:
    """Persist the exception currently being handled; returns the crash ID."""
    crash = MapsCrashReport(
        crash_report_base_path=make_crash_report_base_path(omd_root),
        crash_info=MapsCrashReport.make_crash_info(
            cmk_version_info.get_general_version_infos(omd_root), None
        ),
    )
    CrashReportStore().save(crash)
    return crash.ident_to_text()
