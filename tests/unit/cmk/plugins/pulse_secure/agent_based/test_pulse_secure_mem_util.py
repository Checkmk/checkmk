#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.plugins.pulse_secure.agent_based.pulse_secure_mem_util import (
    check_pulse_secure_mem,
    discover_pulse_secure_mem_util,
    parse_pulse_secure_mem,
    PulseSecureMemUtilParams,
)


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


@pytest.mark.parametrize(
    "params, info, expected_states, expected_labels",
    [
        (
            {"mem_used_percent": (90, 95), "swap_used_percent": (5, 101)},
            [["8", "0"]],
            [State.OK, State.OK],
            ["RAM used", "Swap used"],
        ),
    ],
)
def test_check_pulse_secure_mem(
    params: PulseSecureMemUtilParams,
    info: StringTable,
    expected_states: Sequence[State],
    expected_labels: Sequence[str],
) -> None:
    """Test check function for pulse_secure_mem_util check."""
    parsed = parse_pulse_secure_mem(info)
    assert parsed is not None
    results = list(check_pulse_secure_mem(params, parsed))
    result_objs = [r for r in results if isinstance(r, Result)]
    metric_objs = [r for r in results if isinstance(r, Metric)]
    assert len(result_objs) == len(expected_states)
    for result_obj, expected_state, expected_label in zip(
        result_objs, expected_states, expected_labels
    ):
        assert result_obj.state == expected_state
        assert expected_label in result_obj.summary
    assert len(metric_objs) == 2
