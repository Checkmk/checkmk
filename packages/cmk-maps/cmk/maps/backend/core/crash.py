#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checkmk crash reports for the Maps daemon.

Unhandled request exceptions are persisted through the regular Checkmk crash
report store (``var/check_mk/crashes/maps/``), so they appear on the site's
crash reports page and can be submitted like any other component's crashes.
"""

from pathlib import Path
from typing import override

import cmk.ccc.version_info as cmk_version_info
from cmk.crash import ABCCrashReport, CrashReportStore, make_crash_report_base_path


class MapsCrashReport(ABCCrashReport[None]):
    @override
    @classmethod
    def type(cls) -> str:
        return "maps"


def crash_report(omd_root: Path) -> MapsCrashReport:
    """The report of the exception currently being handled, so it is made where it
    is handled."""
    return MapsCrashReport(
        crash_report_base_path=make_crash_report_base_path(omd_root),
        crash_info=MapsCrashReport.make_crash_info(
            cmk_version_info.get_general_version_infos(omd_root), None
        ),
    )


def save_crash_report(crash: MapsCrashReport) -> str:
    """Persist *crash*; returns the crash ID."""
    CrashReportStore().save(crash)
    return crash.ident_to_text()
