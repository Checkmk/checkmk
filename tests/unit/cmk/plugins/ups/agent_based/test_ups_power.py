#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.internal import evaluate_snmp_detection
from cmk.agent_based.v2 import StringTable
from cmk.plugins.ups.agent_based import ups_power

# walks/usv-liebert
DATA0: dict[str, str] = {
    ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.476.1.42",
}


def test_ups_power_detect() -> None:
    assert evaluate_snmp_detection(
        detect_spec=ups_power.snmp_section_ups_power.detect, oid_value_getter=DATA0.get
    )


@pytest.mark.parametrize(
    "string_table, section",
    [
        pytest.param(
            [[["1", ""]]],
            {},
            id="empty power",
        ),
        pytest.param(
            [[["1", "2"]]],
            {"1": 2},
            id="power present",
        ),
        pytest.param(
            [[["1", "0"]]],
            {"1": 0},
            id="power is zero",
        ),
    ],
)
def test_ups_power_check(string_table: Sequence[StringTable], section: dict[str, int]) -> None:
    assert ups_power.parse_ups_power(string_table) == section
