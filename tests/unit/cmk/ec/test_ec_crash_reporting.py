#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.crash_reporting import crash_report_registry

from cmk.ec.crash_reporting import CrashReportStore, ECCrashReport


def test_ec_crash_report_registry() -> None:
    assert crash_report_registry["ec"] == ECCrashReport


def test_ec_crash_report_from_exception() -> None:
    try:
        raise ValueError("DING")
    except Exception:
        crash = ECCrashReport.from_exception()
        CrashReportStore().save(crash)

    assert crash.type() == "ec"
    assert crash.crash_info["exc_value"] == "DING"
