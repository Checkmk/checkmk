#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.legacy_checks.quanta_voltage import check_quanta_voltage, discover_quanta_voltage
from cmk.plugins.quanta.lib import parse_quanta

_INFO: list[StringTable] = [
    [
        ["1", "3", "Volt_P12V", "12240", "12600", "-99", "-99", "11400"],
        ["2", "3", "Volt_P1V05", "1058", "1200", "1000", "-99", "989"],
        ["3", "3", "Volt_P1V8_AUX", "100", "2000", "1000", "-99", "1705"],
        ["4", "3", "Volt_P3V3", "3370", "3466", "-99", "-99", "3132"],
        ["5", "3", "Volt_P3V3_AUX", "3370", "34000", "-99", "4000", "5000"],
        ["6", "3", "Volt_P3V_BAT", "3161", "38000", "-99", "2000", "1600"],
        ["7", "3", "Volt_P5V", "5009", "5251", "-99", "-99", "4743"],
        ["17", "3", "Volt_SAS_EXP_3V3\x01", "3302", "4000", "3000", "-99", "2958"],
        ["18", "3", "Volt_SAS_EXP_VCC\x01", "3276", "3000", "2800", "-99", "2964"],
    ]
]


def test_discover_quanta_voltage() -> None:
    parsed = parse_quanta(_INFO)
    result = sorted(discover_quanta_voltage(parsed), key=lambda s: s.item or "")
    assert result == [
        Service(item="Volt_P12V"),
        Service(item="Volt_P1V05"),
        Service(item="Volt_P1V8_AUX"),
        Service(item="Volt_P3V3"),
        Service(item="Volt_P3V3_AUX"),
        Service(item="Volt_P3V_BAT"),
        Service(item="Volt_P5V"),
        Service(item="Volt_SAS_EXP_3V3"),
        Service(item="Volt_SAS_EXP_VCC"),
    ]


@pytest.mark.parametrize(
    "item, expected_results",
    [
        (
            "Volt_P12V",
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(state=State.OK, summary="12240.00 V"),
                Metric("voltage", 12240.0, levels=(12600.0, 12600.0)),
            ],
        ),
        (
            "Volt_P1V05",
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(
                    state=State.WARN,
                    summary="1058.00 V (warn/crit at 1000.00 V/1200.00 V)",
                ),
                Metric("voltage", 1058.0, levels=(1000.0, 1200.0)),
            ],
        ),
        (
            "Volt_P1V8_AUX",
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(
                    state=State.CRIT,
                    summary="100.00 V (warn/crit below 1705.00 V/1705.00 V)",
                ),
                Metric("voltage", 100.0, levels=(1000.0, 2000.0)),
            ],
        ),
        (
            "Volt_P3V3",
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(state=State.OK, summary="3370.00 V"),
                Metric("voltage", 3370.0, levels=(3466.0, 3466.0)),
            ],
        ),
        (
            "Volt_P3V3_AUX",
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(
                    state=State.CRIT,
                    summary="3370.00 V (warn/crit below 4000.00 V/5000.00 V)",
                ),
                Metric("voltage", 3370.0, levels=(34000.0, 34000.0)),
            ],
        ),
        (
            "Volt_P3V_BAT",
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(state=State.OK, summary="3161.00 V"),
                Metric("voltage", 3161.0, levels=(38000.0, 38000.0)),
            ],
        ),
        (
            "Volt_P5V",
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(state=State.OK, summary="5009.00 V"),
                Metric("voltage", 5009.0, levels=(5251.0, 5251.0)),
            ],
        ),
        (
            "Volt_SAS_EXP_3V3",
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(
                    state=State.WARN,
                    summary="3302.00 V (warn/crit at 3000.00 V/4000.00 V)",
                ),
                Metric("voltage", 3302.0, levels=(3000.0, 4000.0)),
            ],
        ),
        (
            "Volt_SAS_EXP_VCC",
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(
                    state=State.CRIT,
                    summary="3276.00 V (warn/crit at 2800.00 V/3000.00 V)",
                ),
                Metric("voltage", 3276.0, levels=(2800.0, 3000.0)),
            ],
        ),
    ],
)
def test_check_quanta_voltage(item: str, expected_results: Sequence[object]) -> None:
    parsed = parse_quanta(_INFO)
    result = list(check_quanta_voltage(item, {}, parsed))
    assert result == expected_results
