#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import override

from cmk.ccc import version
from cmk.ccc.crash_reporting import ABCCrashReport, CrashReportStore, VersionInfo
from cmk.utils.paths import crash_dir, omd_root


class _OMDCrashReport(ABCCrashReport[VersionInfo]):
    @classmethod
    @override
    def type(cls) -> str:
        return "omd"


def report_crash() -> str:
    crash = _OMDCrashReport(
        crash_dir, _OMDCrashReport.make_crash_info(version.get_general_version_infos(omd_root))
    )
    CrashReportStore().save(crash)
    return crash.ident_to_text()
