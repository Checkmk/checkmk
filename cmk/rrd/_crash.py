#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys

from cmk.ccc.crash_reporting import (
    ABCCrashReport,
    BaseDetails,
    CrashInfo,
    CrashReportStore,
    make_crash_report_base_path,
    VersionInfo,
)
from cmk.ccc.version import get_general_version_infos
from cmk.utils import paths


def create_crash_report() -> None:
    CrashReportStore().save(
        CMKBaseCrashReport(
            crash_report_base_path=make_crash_report_base_path(paths.omd_root),
            crash_info=CMKBaseCrashReport.make_crash_info(
                get_general_version_infos(paths.omd_root)
            ),
        )
    )


class CMKBaseCrashReport(ABCCrashReport[BaseDetails]):
    @classmethod
    def type(cls) -> str:
        return "base"

    @classmethod
    def make_crash_info(
        cls,
        version_info: VersionInfo,
        _details: BaseDetails | None = None,
    ) -> CrashInfo[BaseDetails]:
        # yurks
        details = BaseDetails(
            argv=sys.argv,
            env=dict(os.environ),
        )
        return super().make_crash_info(version_info, details)
