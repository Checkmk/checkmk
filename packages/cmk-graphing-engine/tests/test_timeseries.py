#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing_engine import constant_time_series, TimeRange, timestamps


def test_each_point_sits_at_the_end_of_its_step() -> None:
    assert timestamps(TimeRange(start=0, end=180, step=60)) == [60, 120, 180]


def test_a_partial_last_step_holds_no_point() -> None:
    assert timestamps(TimeRange(start=0, end=150, step=60)) == [60, 120]


def test_a_range_without_a_step_holds_no_point() -> None:
    assert timestamps(TimeRange(start=0, end=180, step=0)) == []


def test_a_constant_series_has_one_value_per_point() -> None:
    time_range = TimeRange(start=0, end=150, step=60)

    assert len(constant_time_series(1.0, time_range).values) == len(timestamps(time_range))
