#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping

import pytest

from .checktestlib import assertCheckResultsEqual, BasicCheckResult, Check, CheckResult


@pytest.mark.parametrize(
    ["item", "params", "expected"],
    [
        pytest.param(
            "1",
            {},
            [
                BasicCheckResult(0, "Voltage: 230.00 V", [("volt", 230.0, None, None)]),
                BasicCheckResult(0, "Power: 230.00 W"),
                BasicCheckResult(0, "Current: 1.00 A"),
                BasicCheckResult(0, "Load: -1.00 %", [("load_perc", -1.0)]),
            ],
            id="No param",
        ),
        pytest.param(
            "1",
            {"output_voltage_max": (120, 240)},
            [
                BasicCheckResult(
                    1,
                    "Voltage: 230.00 V (warn/crit at 120.00 V/240.00 V)",
                    [("volt", 230.0, 120, 240)],
                ),
                BasicCheckResult(0, "Power: 230.00 W"),
                BasicCheckResult(0, "Current: 1.00 A"),
                BasicCheckResult(0, "Load: -1.00 %", [("load_perc", -1.0)]),
            ],
            id="Upper level for voltage",
        ),
        pytest.param(
            "1",
            {
                "output_voltage_max": (120, 240),
                "output_voltage_min": (10, 20),
            },
            [
                BasicCheckResult(
                    1,
                    "Voltage: 230.00 V (warn/crit at 120.00 V/240.00 V)",
                    [("volt", 230.0, 120, 240)],
                ),
                BasicCheckResult(0, "Power: 230.00 W"),
                BasicCheckResult(0, "Current: 1.00 A"),
                BasicCheckResult(0, "Load: -1.00 %", [("load_perc", -1.0)]),
            ],
            id="Upper level for voltage",
        ),
        pytest.param(
            "1",
            {"load_perc_min": (10.0, 12.0)},
            [
                BasicCheckResult(0, "Voltage: 230.00 V", [("volt", 230.0, None, None)]),
                BasicCheckResult(0, "Power: 230.00 W"),
                BasicCheckResult(0, "Current: 1.00 A"),
                BasicCheckResult(
                    2, "Load: -1.00 % (warn/crit below 10.00 %/12.00 %)", [("load_perc", -1.0)]
                ),
            ],
            id="Lower level for load",
        ),
    ],
)
def test_apc_ats_output_check(
    item: str, params: Mapping[str, tuple[float, float]], expected: Iterable[BasicCheckResult]
) -> None:
    check = Check("apc_ats_output")

    info = {
        "1": {
            "voltage": 230.0,
            "current": 1.0,
            "perc_load": -1.0,
            "power": 230.0,
        },
    }

    result = CheckResult(check.run_check(item, params, info))

    assertCheckResultsEqual(result, CheckResult(expected))
