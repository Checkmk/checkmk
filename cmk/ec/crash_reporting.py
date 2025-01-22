#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Event console specific crash report."""

import cmk.ccc.crash_reporting

CrashReportStore = cmk.ccc.crash_reporting.CrashReportStore


@cmk.ccc.crash_reporting.crash_report_registry.register
class ECCrashReport(cmk.ccc.crash_reporting.ABCCrashReport[cmk.ccc.crash_reporting.VersionInfo]):
    @classmethod
    def type(cls) -> str:
        return "ec"
