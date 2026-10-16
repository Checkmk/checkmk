#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from cmk.base.legacy_checks.silverpeak_VX6000 import check_silverpeak, parse_silverpeak


def test_check_silverpeak_VX6000_alarm_count_without_alarm_rows() -> None:
    # Crash group 4960: the device reported three active alarms, but its alarm
    # table delivered no rows.
    parsed = parse_silverpeak([[["3"]], []])
    assert list(check_silverpeak(None, {}, parsed)) == [
        (0, "3 active alarms. OK: 0, WARN: 0, CRIT: 0, UNKNOWN: 0"),
        (3, "Device reports 3 active alarms but delivered no alarm details"),
    ]
