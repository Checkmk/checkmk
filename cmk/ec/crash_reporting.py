#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Event console specific crash report."""

import cmk.ccc.crash_reporting


class ECCrashReport(cmk.ccc.crash_reporting.ABCCrashReport[None]):
    @classmethod
    def type(cls) -> str:
        return "ec"
