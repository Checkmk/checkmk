#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Shared SNMP detection for the F5OS rSeries plugin family."""

from cmk.agent_based.v2 import all_of, contains, startswith

DETECT_F5OS_RSERIES = all_of(
    contains(".1.3.6.1.2.1.1.1.0", "rSeries"),
    startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12276.1.3."),
)
