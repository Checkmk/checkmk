#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import traceback
from typing import Literal

import cmk.ccc.version as cmk_version
import cmk.utils.paths
from cmk.ccc import crash_reporting
from cmk.ccc.crash_reporting import VersionInfo

CrashReportStore = crash_reporting.CrashReportStore


@crash_reporting.crash_report_registry.register
class AgentCrashReport(crash_reporting.ABCCrashReport[VersionInfo]):
    @classmethod
    def type(cls) -> Literal["agent"]:
        return "agent"


def create_agent_crash_dump() -> str:
    try:
        crash = AgentCrashReport(
            cmk.utils.paths.crash_dir,
            AgentCrashReport.make_crash_info(
                cmk_version.get_general_version_infos(cmk.utils.paths.omd_root)
            ),
        )
        CrashReportStore().save(crash)
        return f"Agent failed - please submit a crash report! (Crash-ID: {crash.ident_to_text()})"
    except Exception:
        return f"Agent failed - failed to create a crash report: {traceback.format_exc()}"
