#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import collections
from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import Result, State
from cmk.legacy_checks.nimble_latency import (
    check_nimble_latency_reads,
    check_nimble_latency_writes,
    LatencyData,
    ParsedNimbleLatency,
)

range_data: LatencyData = {
    "total": 20,
    "ranges": collections.OrderedDict(
        [
            ("0.1", ("0-0.1 ms", 0)),
            ("0.2", ("0.1-0.2 ms", 0)),
            ("0.5", ("0.2-0.5 ms", 2)),
            ("1", ("0.5-1.0 ms", 1)),
            ("2", ("1-2 ms", 1)),
            ("5", ("2-5 ms", 1)),
            ("10", ("5-10 ms", 10)),
            ("20", ("10-20 ms", 1)),
            ("50", ("20-50 ms", 1)),
            ("100", ("50-100 ms", 1)),
            ("200", ("100-200 ms", 1)),
            ("500", ("200-500 ms", 1)),
            ("1000", ("500+ ms", 0)),
        ]
    ),
}

Param = Mapping[str, str | tuple[float, float]]


@pytest.mark.parametrize(
    "params, data, expected",
    [
        (
            {"range_reference": "0.1", "read": (99, 100)},
            {"itemxyz": {"read": range_data}},
            Result(
                state=State.CRIT,
                summary="At or above 0-0.1 ms: 100.00% (warn/crit at 99.00%/100.00%)",
            ),
        ),
        (
            {"range_reference": "50", "read": (99, 100)},
            {"itemxyz": {"read": range_data}},
            Result(state=State.OK, summary="At or above 20-50 ms: 20.00%"),
        ),
        (
            {"range_reference": "1000", "read": (99, 100)},
            {"itemxyz": {"read": range_data}},
            Result(state=State.OK, summary="At or above 500+ ms: 0%"),
        ),
    ],
)
def test_nimble_latency_ranges(
    params: Param,
    data: ParsedNimbleLatency,
    expected: Result,
) -> None:
    """The user can specify a parameter range_reference, which serves as a starting
    point from which values should start to be stacked and checked against levels.
    Test whether the stacking is correct."""
    actual_results = list(check_nimble_latency_reads("itemxyz", params, data))
    assert actual_results[0] == expected


def test_nimble_latency_read_params() -> None:
    """Test that latency read levels are applied to read types only."""
    params: Param = {
        "range_reference": "50",
        "read": (30, 40),
        "write": (1, 2),
    }
    data: ParsedNimbleLatency = {"itemxyz": {"read": range_data}}
    expected = Result(state=State.OK, summary="At or above 20-50 ms: 20.00%")

    read_results = list(check_nimble_latency_reads("itemxyz", params, data))
    write_results = list(check_nimble_latency_writes("itemxyz", params, data))
    assert read_results[0] == expected
    assert not write_results


def test_nimble_latency_write_params() -> None:
    """Test that latency write levels are applied to write types only."""
    params: Param = {
        "range_reference": "50",
        "read": (30, 40),
        "write": (1, 2),
    }
    data: ParsedNimbleLatency = {"itemxyz": {"write": range_data}}
    expected = Result(
        state=State.CRIT,
        summary="At or above 20-50 ms: 20.00% (warn/crit at 1.00%/2.00%)",
    )

    read_results = list(check_nimble_latency_reads("itemxyz", params, data))
    write_results = list(check_nimble_latency_writes("itemxyz", params, data))
    assert write_results[0] == expected
    assert not read_results
