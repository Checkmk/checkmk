#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pathlib import Path
from typing import override

from cmk.ccc import version
from cmk.ccc.crash_reporting import ABCCrashReport, CrashReportStore, make_crash_report_base_path


class _OMDCrashReport(ABCCrashReport[None]):
    @classmethod
    @override
    def type(cls) -> str:
        return "omd"


def report_crash(site_home: Path) -> str:
    crash = _OMDCrashReport(
        crash_report_base_path=make_crash_report_base_path(site_home),
        crash_info=_OMDCrashReport.make_crash_info(
            version.get_general_version_infos(site_home), None
        ),
    )
    CrashReportStore().save(crash)
    return crash.ident_to_text()
