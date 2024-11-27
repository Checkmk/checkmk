#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping
from contextlib import suppress
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


def _call_size_trend_with(args: ArgsDict) -> list[IgnoreResults | Metric | Result]:
    return list(
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


def test_size_trend(args: ArgsDict) -> None:
    # size_trend returns generator, but we need to evaluate it
    # so the valuestore is written properly
    with suppress(GetRateError):
        _call_size_trend_with(args)

    # New measurement half an hour later with 100MB more
    args.update({"used_mb": 200, "timestamp": 1.0 + 1800})
    # (100 (MB) / 1800) * 3600 * 24
    assert _call_size_trend_with(args) == [
        Metric(name="growth", value=4800.0),
        Result(state=State.OK, summary="trend per 1 hour 0 minutes: +200 MiB"),
        Result(state=State.OK, summary="trend per 1 hour 0 minutes: +10.00%"),
        Metric("trend", 4800.0),
        Result(state=State.OK, summary="Time left until resource_name full: 9 hours 0 minutes"),
    ]


def test_size_trend_full_in_eternity(args: ArgsDict) -> None:
    # size_trend returns generator, but we need to evaluate it
    # so the valuestore is written properly
    with suppress(GetRateError):
        _call_size_trend_with(args)

    # simulate a very low trend
    args.update({"used_mb": 100.00001, "timestamp": 1.0 + 1800})
    assert _call_size_trend_with(args) == [
        Metric("growth", 0.0004800000001523585),
        Result(state=State.OK, summary="trend per 1 hour 0 minutes: +21 B"),
        Result(state=State.OK, summary="trend per 1 hour 0 minutes: +<0.01%"),
        Metric("trend", 0.0004800000001523585),
    ]


def test_size_trend_growing(args: ArgsDict) -> None:
    with suppress(GetRateError):
        _call_size_trend_with(args)

    args["levels"] = {
        "trend_range": 1,
        "trend_perfdata": True,
        "trend_bytes": (150 * 1024**2, 250 * 1024**2),
        "trend_perc": (5.0, 15.0),
    }
    args.update({"used_mb": 200, "timestamp": 1801.0})
    assert _call_size_trend_with(args) == [
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
        Result(state=State.OK, summary="Time left until resource_name full: 9 hours 0 minutes"),
    ]


def test_size_trend_shrinking_ok(args: ArgsDict) -> None:
    args["used_mb"] = 1000
    with suppress(GetRateError):
        _call_size_trend_with(args)

    args["levels"] = {
        "trend_range": 1,
        "trend_perfdata": True,
        "trend_shrinking_bytes": (100 * 1024**2, 200 * 1024**2),
        "trend_shrinking_perc": (5.0, 10.0),
    }
    args.update(
        {
            "timestamp": 1801.0,
            "used_mb": 990,
        }
    )
    assert _call_size_trend_with(args) == [
        Metric(name="growth", value=-480.0),
        Result(state=State.OK, summary="trend per 1 hour 0 minutes: -20.0 MiB"),
        Result(state=State.OK, summary="trend per 1 hour 0 minutes: -1.00%"),
        Metric("trend", -480.0),
    ]


def test_size_trend_shrinking_warn(args: ArgsDict) -> None:
    args["used_mb"] = 1000
    with suppress(GetRateError):
        _call_size_trend_with(args)

    args["levels"] = {
        "trend_range": 1,
        "trend_perfdata": True,
        "trend_shrinking_bytes": (100 * 1024**2, 200 * 1024**2),
        "trend_shrinking_perc": (5.0, 10.0),
    }
    args.update(
        {
            "timestamp": 1801.0,
            "used_mb": 900,
        }
    )
    assert _call_size_trend_with(args) == [
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


def test_size_trend_negative_free_space() -> None:
    assert list(
        size_trend(
            value_store={
                "vs_key.delta": (50, 101),
            },
            value_store_key="vs_key",
            resource="something",
            levels={
                "trend_range": 1,
                "trend_perfdata": True,
                "trend_timeleft": (12, 6),
            },
            used_mb=130,
            size_mb=123,
            timestamp=100,
        )
    ) == [
        Metric("growth", 50112.0),
        Result(state=State.OK, summary="trend per 1 hour 0 minutes: +2.04 GiB"),
        Result(state=State.OK, summary="trend per 1 hour 0 minutes: +1697.56%"),
        Metric("trend", 50112.0),
        Result(
            state=State.CRIT,
            summary="Time left until something full: 0 seconds (warn/crit below 12 hours 0 minutes/6 hours 0 minutes)",
        ),
    ]


def test_size_trend_infinite() -> None:
    assert list(
        size_trend(
            value_store={
                "vs_key.delta": (100, 3 * 10**-322),
            },
            value_store_key="vs_key",
            resource="something",
            levels={
                "trend_range": 1,
                "trend_perfdata": True,
            },
            used_mb=3 * 10**-321,
            size_mb=123,
            timestamp=101,
        )
    ) == [
        Metric("growth", 2.33072504e-316),
        Result(state=State.OK, summary="trend per 1 hour 0 minutes: +0 B"),
        Result(state=State.OK, summary="trend per 1 hour 0 minutes: +<0.01%"),
        Metric("trend", 2.33072504e-316),
    ]
