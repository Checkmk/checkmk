#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.agent_based.v2 import Result, State
from cmk.plugins.lib.uptime import check, parse_snmp_uptime


@pytest.mark.xfail(
    strict=True,
    raises=ValueError,
    reason="Crash report e279d6b6-d12e-11f1-b32d-0050569e8de8: ValueError negative timespan",
)
def test_check_snmp_uptime_ignores_negative_hr_system_up_time() -> None:
    # The device reports hrSystemUptime as a signed 32 bit value, which turns
    # negative after about 248 days of uptime. sysUpTime is still valid.
    section = parse_snmp_uptime([["2297331594", "-2138089800"]])
    assert section is not None

    assert Result(state=State.OK, summary="Uptime: 265 days 21 hours") in list(check({}, section))
