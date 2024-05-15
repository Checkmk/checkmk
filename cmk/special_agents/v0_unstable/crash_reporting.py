#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import traceback
from typing import Literal

import cmk.utils.crash_reporting as crash_reporting

CrashReportStore = crash_reporting.CrashReportStore


@crash_reporting.crash_report_registry.register
class AgentCrashReport(crash_reporting.ABCCrashReport):
    @classmethod
    def type(cls) -> Literal["agent"]:
        return "agent"


def create_agent_crash_dump() -> str:
    try:
        crash = AgentCrashReport.from_exception()
        CrashReportStore().save(crash)
        return f"Agent failed - please submit a crash report! (Crash-ID: {crash.ident_to_text()})"
    except Exception:
        return f"Agent failed - failed to create a crash report: {traceback.format_exc()}"
