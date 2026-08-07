#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class TimeRange:
    start: int
    end: int
    step: int


class ConsolidationFunction(enum.StrEnum):
    # How the samples falling into one step of the range collapse into the single point drawn for it.
    MIN = "min"
    MAX = "max"
    AVERAGE = "average"


@dataclass(frozen=True, kw_only=True)
class TimeSeries:
    time_range: TimeRange
    values: Sequence[float | None]


def _num_points(time_range: TimeRange) -> int:
    if time_range.step <= 0:
        return 0
    return max(0, (time_range.end - time_range.start) // time_range.step)


def constant_time_series(value: float | None, time_range: TimeRange) -> TimeSeries:
    # The same value at every point of the range - the shape a quantity without a fetched series of
    # its own draws on: a constant, a threshold, or a present-but-all-None curve.
    return TimeSeries(time_range=time_range, values=[value] * _num_points(time_range))
