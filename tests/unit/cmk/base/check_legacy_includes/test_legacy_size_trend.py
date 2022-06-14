#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from _pytest.monkeypatch import MonkeyPatch

from cmk.base.check_legacy_includes import size_trend


def patch_rate_and_average(monkeypatch: MonkeyPatch, negative: bool = False) -> None:
    # growth is in MB/s
    growth = 100 / 3600
    if negative:
        growth *= -1

    monkeypatch.setattr(size_trend, "get_rate", lambda *_args, **_kwargs: growth)
    monkeypatch.setattr(size_trend, "get_average", lambda *_args: growth)


def test_size_trend_growing(monkeypatch: MonkeyPatch) -> None:
    patch_rate_and_average(monkeypatch, False)
    state, infotext, perfdata = size_trend.size_trend(
        "somecheck",
        "someitem",
        "some resource",
        {
            "trend_range": 1,
            "trend_perfdata": True,
            "trend_bytes": (50 * 1024**2, 100 * 1024**2),
            "trend_shrinking_bytes": (50 * 1024**2, 100 * 1024**2),
            "trend_perc": (10, 20),
            "trend_shrinking_perc": (10, 20),
            "trend_timeleft": (72, 48),
            "trend_showtimeleft": True,
        },
        100.0,
        1000.0,
        1800.0,
    )
    assert state == 2
    assert (
        infotext
        == ", trend: +100 MiB / 1 hours - growing too fast (warn/crit at 50.0 MiB/100 MiB per 1.0 h)(!!)"
        ", growing too fast (warn/crit at 10.0%/20.0% per 1.0 h)(!)"
        ", only 9 hours until some resource full(!!)"
    )
    assert perfdata == [
        ("growth", 2400.0),
        ("trend", 2400.0, 1200.0, 2400.0, 0, 1000.0),
        ("trend_hoursleft", 9.0),
    ]


def test_size_trend_shrinking(monkeypatch: MonkeyPatch) -> None:
    patch_rate_and_average(monkeypatch, True)
    state, infotext, perfdata = size_trend.size_trend(
        "somecheck",
        "someitem",
        "some resource",
        {
            "trend_range": 1,
            "trend_perfdata": True,
            "trend_bytes": (50 * 1024**2, 100 * 1024**2),
            "trend_shrinking_bytes": (50 * 1024**2, 100 * 1024**2),
            "trend_perc": (10, 20),
            "trend_shrinking_perc": (10, 20),
            "trend_timeleft": (72, 48),
            "trend_showtimeleft": True,
        },
        100.0,
        1000.0,
        1800.0,
    )
    assert state == 2
    assert (
        infotext
        == ", trend: -100 MiB / 1 hours - shrinking too fast (warn/crit at 50.0 MiB/100 MiB per 1.0 h)(!!)"
        ", shrinking too fast (warn/crit at 10.0%/20.0% per 1.0 h)(!)"
    )
    assert perfdata == [
        ("growth", -2400.0),
        ("trend", -2400.0, 1200.0, 2400.0, 0, 1000.0),
        ("trend_hoursleft", -1),
    ]
