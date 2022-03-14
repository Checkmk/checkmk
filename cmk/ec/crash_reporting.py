#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Event console specific crash report"""

import cmk.utils.crash_reporting

CrashReportStore = cmk.utils.crash_reporting.CrashReportStore


@cmk.utils.crash_reporting.crash_report_registry.register
class ECCrashReport(cmk.utils.crash_reporting.ABCCrashReport):
    @classmethod
    def type(cls):
        return "ec"
