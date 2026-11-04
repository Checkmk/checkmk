#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Background crash report consolidation job.

Server-side programs (agents, active checks) write crash reports via
``cmk-plugin-apis``'s ``_crash_reporting`` module, which bypasses
``CrashReportStore`` and writes files directly in the legacy v0 format
(``time: float``).  This job runs periodically to migrate, deduplicate,
and prune all crash type directories.
"""

import cmk.utils.paths
from cmk.crash import CrashReportStore, make_crash_report_base_path
from cmk.gui.config import Config


def consolidate_crash_reports(_config: Config) -> None:
    CrashReportStore().consolidate_all_crash_dirs(
        make_crash_report_base_path(cmk.utils.paths.omd_root)
    )
