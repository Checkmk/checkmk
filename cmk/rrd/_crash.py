#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys
from pathlib import Path

from cmk.ccc.version_info import get_general_version_infos
from cmk.crash import (
    BaseCrashReport,
    BaseDetails,
    CrashReportStore,
    make_crash_report_base_path,
)


def create_crash_report(omd_root: Path) -> None:
    CrashReportStore().save(
        BaseCrashReport(
            crash_report_base_path=make_crash_report_base_path(omd_root),
            crash_info=BaseCrashReport.make_crash_info(
                get_general_version_infos(omd_root),
                BaseDetails(argv=sys.argv, env=dict(os.environ)),
            ),
        )
    )
