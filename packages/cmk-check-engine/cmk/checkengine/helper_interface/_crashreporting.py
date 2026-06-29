#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check_MK base specific code of the crash reporting"""

import os
import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Self

from cmk.ccc.crash_reporting import ABCCrashReport, BaseDetails, CrashReportStore, VersionInfo


def create_fetcher_crash_dump(
    *,
    serial: str | None,
    host: str | None,
    crash_report_base_path: Path,
    get_general_version_infos: Callable[[], VersionInfo],
    debug: bool,
) -> str:
    """Create a crash dump from an exception occurred during fetcher execution

    The crash dump is put into a tarball, base64 encoded and appended to the long output
    of the check. The GUI (cmk.gui.crash_reporting) is able to parse it and send it to
    the Checkmk team.
    """
    text = "fetcher failed - please submit a crash report!"
    try:
        crash = CMKFetcherCrashReport.from_exception_and_context(
            crash_report_base_path=crash_report_base_path,
            get_general_version_infos=get_general_version_infos,
            serial=serial,
            host=host,
        )
        CrashReportStore().save(crash)
        text += " (Crash-ID: %s)" % crash.ident_to_text()
        return text
    except Exception:
        if debug:
            raise
        return "fetcher failed - failed to create a crash report: %s" % traceback.format_exc()


class FetcherDetails(BaseDetails):
    serial: str | None
    host: str | None


class CMKFetcherCrashReport(ABCCrashReport[FetcherDetails]):
    @classmethod
    def type(cls) -> str:
        return "fetcher"

    @classmethod
    def from_exception_and_context(
        cls,
        *,
        crash_report_base_path: Path,
        get_general_version_infos: Callable[[], VersionInfo],
        serial: str | None,
        host: str | None,
    ) -> Self:
        return cls(
            crash_report_base_path=crash_report_base_path,
            crash_info=cls.make_crash_info(
                get_general_version_infos(),
                details=FetcherDetails(
                    argv=sys.argv,
                    env=dict(os.environ),
                    serial=serial,
                    host=host,
                ),
            ),
        )
