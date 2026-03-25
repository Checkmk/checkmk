#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

import cmk.utils.paths
from cmk.crash import CrashReportStore, make_crash_report_base_path
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction


class MigrateCrashReports(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        CrashReportStore().consolidate_all_crash_dirs(
            make_crash_report_base_path(cmk.utils.paths.omd_root)
        )


update_action_registry.register(
    MigrateCrashReports(
        name="migrate_crash_reports",
        title="Crash reports: Migrate to grouped format with occurrence tracking",
        sort_index=150,
        expiry_version=ExpiryVersion.CMK_310,
    )
)
