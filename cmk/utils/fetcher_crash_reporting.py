#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check_MK base specific code of the crash reporting"""

import os
import sys
import traceback

import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.encoding
import cmk.utils.crash_reporting as crash_reporting
from cmk.utils.type_defs import ConfigSerial

CrashReportStore = crash_reporting.CrashReportStore


def create_fetcher_crash_dump(
    serial: ConfigSerial,
    host: str,
) -> str:
    """Create a crash dump from an exception occured during fetcher execution

    The crash dump is put into a tarball, base64 encoded and appended to the long output
    of the check. The GUI (cmk.gui.crash_reporting) is able to parse it and send it to
    the Checkmk team.
    """
    text = u"fetcher failed - please submit a crash report!"
    try:
        crash = CMKFetcherCrashReport.from_exception_and_context(
            host=host,
            serial=serial,
        )
        CrashReportStore().save(crash)
        text += " (Crash-ID: %s)" % crash.ident_to_text()
        return text
    except Exception:
        if cmk.utils.debug.enabled():
            raise
        return "fetcher failed - failed to create a crash report: %s" % traceback.format_exc()


@crash_reporting.crash_report_registry.register
class CMKFetcherCrashReport(crash_reporting.ABCCrashReport):
    @classmethod
    def type(cls) -> str:
        return "fetcher"

    @classmethod
    def from_exception_and_context(cls, serial: ConfigSerial,
                                   host: str) -> crash_reporting.ABCCrashReport:
        return super(CMKFetcherCrashReport, cls).from_exception(details={
            "argv": sys.argv,
            "env": dict(os.environ),
            "serial": serial,
            "host": host,
        })
