#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


import pytest

from cmk.base.legacy_checks.megaraid_bbu import (
    check_megaraid_bbu,
    discover_megaraid_bbu,
    megaraid_bbu_parse,
)


@pytest.fixture(scope="function", name="section")
def _get_section():
    return megaraid_bbu_parse(
        [
            line.split()
            for line in """
BBU status for Adapter: 0

BatteryType: CVPM02
Voltage: 9437 mV
Current: 0 mA
Temperature: 27 C
BBU Firmware Status:

Charging Status : None
Voltage : OK
Temperature : OK
Learn Cycle Requested : No
Learn Cycle Active : No
Learn Cycle Status : OK
Learn Cycle Timeout : No
I2c Errors Detected : No
Battery Pack Missing : No
Battery Replacement required : No
Remaining Capacity Low : No
Periodic Learn Required : No
Transparent Learn : No
No space to cache offload : No
Pack is about to fail & should be replaced : No
Cache Offload premium feature required : No
Module microcode update required : No
BBU GasGauge Status: 0x6ef7
Pack energy : 247 J
Capacitance : 110
Remaining reserve space : 0
""".split("\n")
            if line
        ]
    )


def test_discovery(section: object) -> None:
    assert list(discover_megaraid_bbu(section)) == [("/c0", {})]


def test_check_ok(section: object) -> None:
    result = list(check_megaraid_bbu("/c0", {}, section))
    assert result == [
        (0, "Charge: not reported for this controller"),
        (0, "All states as expected"),
    ]


def test_check_low_cap(section: dict[str, dict[str, str]]) -> None:
    section["0"]["Remaining Capacity Low"] = "Yes"
    result = list(check_megaraid_bbu("/c0", {}, section))
    assert result == [
        (0, "Charge: not reported for this controller"),
        (1, "Remaining capacity low: Yes (expected: No)"),
    ]
