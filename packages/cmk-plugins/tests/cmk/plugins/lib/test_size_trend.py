#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Mapping, MutableMapping
from contextlib import AbstractContextManager, nullcontext, suppress
from typing import Any, TypedDict

import pytest

from cmk.agent_based.v1 import GetRateError, IgnoreResults, Metric, Result, State
from cmk.plugins.lib.size_trend import size_trend


class ArgsDict(TypedDict):
    value_store: MutableMapping[str, Any]
    value_store_key: str
    resource: str
    levels: Mapping[str, Any]
    used_mb: float
    size_mb: float
    timestamp: float | None


@pytest.fixture(name="args")
def fixture_args() -> ArgsDict:
    # put in a function so the value_store is always fresh
    return {
        "value_store": {},
        "value_store_key": "vskey",
        "resource": "resource_name",
        "levels": {
            "trend_range": 1,
            "trend_perfdata": True,
        },
        "used_mb": 100.0,
        "size_mb": 2000.0,
        "timestamp": 1.0,
    }


def _call_size_trend_with(
    args: ArgsDict,
    iterations: int = 1,
    time_inc: float = 60.0,
    used_inc: float = 0.0,
    ignore_first_get_rate_error: bool = True,
) -> list[IgnoreResults | Metric | Result]:
    result = []
    cm: AbstractContextManager[None]
    for i in range(iterations):
        if i == 0 and ignore_first_get_rate_error:
            cm = suppress(GetRateError)
        else:
            cm = nullcontext()
        if i > 0:
            if args["timestamp"] is not None:
                args["timestamp"] += time_inc
            args["used_mb"] += used_inc
        with cm:
            result = list(
                size_trend(
                    value_store=args["value_store"],
                    value_store_key=args["value_store_key"],
                    resource=args["resource"],
                    levels=args["levels"],
                    used_mb=args["used_mb"],
                    size_mb=args["size_mb"],
                    timestamp=args["timestamp"],
                )
            )
    return result


def test_size_trend_no_trend_yet(args: ArgsDict) -> None:
    """
    When we don't do enough iterations yet to calculate a trend,
    size_trend should not try to give a trend.
    """
    result = _call_size_trend_with(args, iterations=6)
    assert result == [Result(state=State.OK, summary="Not enough data to calculate trend")]


def test_size_trend_no_trend_yet_upper_bound(args: ArgsDict) -> None:
    """
    This should be the last iteration where we don't have enough data
    """
    result = _call_size_trend_with(args, iterations=61, used_inc=1.0)
    assert result == [Result(state=State.OK, summary="Not enough data to calculate trend")]


def test_size_trend_first_valid_iteration_count(args: ArgsDict) -> None:
    """
    As soon as we get a full period's worth of data, size_trend should return a trend
    on the next iteration.
    """
    result = _call_size_trend_with(args, iterations=62, used_inc=1.0)
    assert result == [
        Metric("growth", 1440.0),
        Result(state=State.OK, summary="trend per 1 hour 0 minutes: +60.0 MiB"),
        Result(state=State.OK, summary="trend per 1 hour 0 minutes: +3.00%"),
        Metric("trend", 1440.0),
        Result(state=State.OK, summary="Time left until resource_name full: 1 day 6 hours"),
    ]


def test_size_trend(args: ArgsDict) -> None:
    assert _call_size_trend_with(args, iterations=4, used_inc=100, time_inc=1800) == [
        Metric(name="growth", value=4800.0),
        Result(state=State.OK, summary="trend per 1 hour 0 minutes: +200 MiB"),
        Result(state=State.OK, summary="trend per 1 hour 0 minutes: +10.00%"),
        Metric("trend", 4800.0),
        Result(state=State.OK, summary="Time left until resource_name full: 8 hours 0 minutes"),
    ]


def test_size_trend_full_in_eternity(args: ArgsDict) -> None:
    """
    Simulate a very low trend
    """
    assert _call_size_trend_with(args, iterations=4, used_inc=0.00001, time_inc=1800) == [
        Metric("growth", 0.0004800000001523585),
        Result(state=State.OK, summary="trend per 1 hour 0 minutes: +21 B"),
        Result(state=State.OK, summary="trend per 1 hour 0 minutes: +<0.01%"),
        Metric("trend", 0.0004800000001523585),
    ]


def test_size_trend_growing(args: ArgsDict) -> None:
    args["levels"] = {
        "trend_range": 1,
        "trend_perfdata": True,
        "trend_bytes": (150 * 1024**2, 250 * 1024**2),
        "trend_perc": (5.0, 15.0),
    }

    assert _call_size_trend_with(args, iterations=4, used_inc=100, time_inc=1800) == [
        Metric(name="growth", value=4800.0),
        Result(
            state=State.WARN,
            summary="trend per 1 hour 0 minutes: +200 MiB (warn/crit at +150 MiB/+250 MiB)",
        ),
        Result(
            state=State.WARN,
            summary="trend per 1 hour 0 minutes: +10.00% (warn/crit at +5.00%/+15.00%)",
        ),
        Metric("trend", 4800.0, levels=(100.0, 250.0)),
        Result(state=State.OK, summary="Time left until resource_name full: 8 hours 0 minutes"),
    ]


def test_size_trend_shrinking_ok(args: ArgsDict) -> None:
    args["used_mb"] = 1000
    args["levels"] = {
        "trend_range": 1,
        "trend_perfdata": True,
        "trend_shrinking_bytes": (100 * 1024**2, 200 * 1024**2),
        "trend_shrinking_perc": (5.0, 10.0),
    }
    assert _call_size_trend_with(args, iterations=4, used_inc=-10, time_inc=1800) == [
        Metric(name="growth", value=-480.0),
        Result(state=State.OK, summary="trend per 1 hour 0 minutes: -20.0 MiB"),
        Result(state=State.OK, summary="trend per 1 hour 0 minutes: -1.00%"),
        Metric("trend", -480.0),
    ]


def test_size_trend_shrinking_warn(args: ArgsDict) -> None:
    args["used_mb"] = 1000
    args["levels"] = {
        "trend_range": 1,
        "trend_perfdata": True,
        "trend_shrinking_bytes": (100 * 1024**2, 200 * 1024**2),
        "trend_shrinking_perc": (5.0, 10.0),
    }
    assert _call_size_trend_with(args, iterations=4, used_inc=-100, time_inc=1800) == [
        Metric(name="growth", value=-4800.0),
        Result(
            state=State.WARN,
            summary="trend per 1 hour 0 minutes: -200 MiB (warn/crit below -100 MiB/-200 MiB)",
        ),
        Result(
            state=State.WARN,
            summary="trend per 1 hour 0 minutes: -10.00% (warn/crit below -5.00%/-10.00%)",
        ),
        Metric("trend", -4800.0),
    ]


def test_size_trend_negative_free_space(args: ArgsDict) -> None:
    args["used_mb"] = 130
    args["size_mb"] = 123
    args["levels"] = {
        "trend_range": 1,
        "trend_perfdata": True,
        "trend_timeleft": (12, 6),
    }
    assert _call_size_trend_with(args, iterations=4, used_inc=1044, time_inc=1800) == [
        Metric("growth", 50112.0),
        Result(state=State.OK, summary="trend per 1 hour 0 minutes: +2.04 GiB"),
        Result(state=State.OK, summary="trend per 1 hour 0 minutes: +1697.56%"),
        Metric("trend", 50112.0),
        Result(
            state=State.CRIT,
            summary="Time left until resource_name full: 0 seconds (warn/crit below 12 hours 0 minutes/6 hours 0 minutes)",
        ),
    ]


def test_size_trend_infinite(args: ArgsDict) -> None:
    args["used_mb"] = 0.0
    args["size_mb"] = 123
    args["resource"] = "something"
    args["value_store_key"] = "vs_key"
    args["levels"] = {
        "trend_range": 1,
        "trend_perfdata": True,
    }
    # Use a tiny increment that will result in the expected extremely small trend
    # The rate should be approximately 2.7e-321 MB/sec to get 2.33072504e-316 MB/day
    tiny_increment = 2.7e-321 * 1800  # MB increase per 1800 seconds
    assert _call_size_trend_with(args, iterations=4, used_inc=tiny_increment, time_inc=1800) == [
        Metric("growth", 2.33072504e-316),
        Result(state=State.OK, summary="trend per 1 hour 0 minutes: +0 B"),
        Result(state=State.OK, summary="trend per 1 hour 0 minutes: +<0.01%"),
        Metric("trend", 2.33072504e-316),
    ]
