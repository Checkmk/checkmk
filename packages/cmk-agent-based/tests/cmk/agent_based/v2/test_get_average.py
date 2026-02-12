#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# pylint: disable=duplicate-code

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import get_average


@pytest.mark.parametrize(
    "backlog_min,timeseries",
    [
        (
            1,
            [
                (0, 23, 23),
                (60, 42, 32.5),
                (120, 42, 37.25),
                (300, 42, 41.40625),
            ],
        ),
    ],
)
def test_get_average(backlog_min: int, timeseries: Sequence[tuple[float, float, float]]) -> None:
    store: dict[str, object] = {}
    for idx, (this_time, this_value, expected_average) in enumerate(timeseries):
        avg = get_average(
            store,
            "foo",
            this_time,
            this_value,
            backlog_min,
        )
        assert avg == expected_average, f"at [{idx!r}]: got {avg!r} expected {expected_average!r}"


@pytest.mark.parametrize(
    "timeseries, expected_averages",
    [
        (
            [
                # Phase 1: epoch timestamps (like 2.2)
                (1718810400.0, 500000.0),
                (1718810460.0, 600000.0),
                # Phase 2: sysUpTime (like 2.3) — backward jump
                (35577158.0, 470000.0),
                # Phase 3: next sysUpTime — should resume normally
                (35577218.0, 480000.0),
            ],
            [500000.0, 550000.0, 550000.0, 540938.5394307286],
        )
    ],
)
def test_get_average_v2_time_goes_backwards_resets(
    timeseries: Sequence[tuple[float, float]], expected_averages: Sequence[float]
) -> None:
    """Simulate 2.2->2.3 migration: time source changes from epoch to sysUpTime."""
    store: dict[str, object] = {}

    # Phase 1: Build up an average using epoch timestamps
    avg = get_average(store, "foo", *timeseries[0], 5)

    assert avg == expected_averages[0]
    avg = get_average(store, "foo", *timeseries[1], 5)
    old_avg = avg

    assert avg == expected_averages[1]

    # Phase 2: Time source switches to sysUpTime (much smaller number)
    avg = get_average(store, "foo", *timeseries[2], 5)

    # After fix: should reset times but preserve the previous average
    assert avg == expected_averages[2]
    assert store["foo"] == (timeseries[0][0], timeseries[2][0], old_avg)

    # Phase 3: Subsequent calls with sysUpTime should work normally
    avg = get_average(store, "foo", *timeseries[3], 5)
    assert avg == expected_averages[3]
