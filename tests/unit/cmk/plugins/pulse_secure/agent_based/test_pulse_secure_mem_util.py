#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.plugins.pulse_secure.agent_based.pulse_secure_mem_util import (
    check_pulse_secure_mem,
    discover_pulse_secure_mem_util,
    parse_pulse_secure_mem,
    PulseSecureMemUtilParams,
)

PARAMS = PulseSecureMemUtilParams(mem_used_percent=(90, 95), swap_used_percent=(5, 101))


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        ([["8", "0"]], [True]),
    ],
)
def test_discover_pulse_secure_mem(info: StringTable, expected_discoveries: Sequence[bool]) -> None:
    """Test discovery function for pulse_secure_mem_util check."""
    parsed = parse_pulse_secure_mem(info)
    if parsed is not None:
        result = list(discover_pulse_secure_mem_util(parsed))
    else:
        result = []
    assert len(result) == len(expected_discoveries)


def test_check_pulse_secure_mem_below_the_levels() -> None:
    parsed = parse_pulse_secure_mem([["8", "0"]])
    assert parsed is not None

    assert list(check_pulse_secure_mem(PARAMS, parsed)) == [
        Result(state=State.OK, summary="RAM used: 8.00%"),
        Metric("mem_used_percent", 8.0, levels=(90.0, 95.0)),
        Result(state=State.OK, summary="Swap used: 0%"),
        Metric("swap_used_percent", 0.0, levels=(5.0, 101.0)),
    ]


def test_check_pulse_secure_mem_above_the_warn_levels() -> None:
    """The default swap crit level of 101% is deliberately out of range, so swap can only WARN."""
    parsed = parse_pulse_secure_mem([["92", "7"]])
    assert parsed is not None

    assert list(check_pulse_secure_mem(PARAMS, parsed)) == [
        Result(state=State.WARN, summary="RAM used: 92.00% (warn/crit at 90.00%/95.00%)"),
        Metric("mem_used_percent", 92.0, levels=(90.0, 95.0)),
        Result(state=State.WARN, summary="Swap used: 7.00% (warn/crit at 5.00%/101.00%)"),
        Metric("swap_used_percent", 7.0, levels=(5.0, 101.0)),
    ]


def test_check_without_configured_levels() -> None:
    parsed = parse_pulse_secure_mem([["8", "0"]])
    assert parsed is not None

    assert list(check_pulse_secure_mem(PulseSecureMemUtilParams(), parsed)) == [
        Result(state=State.OK, summary="RAM used: 8.00%"),
        Metric("mem_used_percent", 8.0),
        Result(state=State.OK, summary="Swap used: 0%"),
        Metric("swap_used_percent", 0.0),
    ]
