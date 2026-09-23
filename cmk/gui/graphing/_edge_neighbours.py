#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Final

from cmk.graphing_engine import TimeRange

_NEIGHBOURS_BEYOND_AN_EDGE: Final = 1
_STEPS_FROM_A_RANGE_START_TO_ITS_FIRST_SAMPLE: Final = 1
_LEADING_NEIGHBOUR_STEPS: Final = (
    _STEPS_FROM_A_RANGE_START_TO_ITS_FIRST_SAMPLE + _NEIGHBOURS_BEYOND_AN_EDGE
)
_TRAILING_NEIGHBOUR_STEPS: Final = _NEIGHBOURS_BEYOND_AN_EDGE


def with_edge_neighbours(window: TimeRange, neighbour_step: int) -> TimeRange:
    return TimeRange(
        start=window.start - _LEADING_NEIGHBOUR_STEPS * neighbour_step,
        end=window.end + _TRAILING_NEIGHBOUR_STEPS * neighbour_step,
        step=window.step,
    )


@dataclass(frozen=True, kw_only=True)
class _Archive:
    step: int
    rows: int

    def served_step_for(self, requested_step: int) -> int:
        return max(self.step, requested_step)

    def surely_reaches_back_to(self, time: int, *, latest_possible_update: float) -> bool:
        return time >= latest_possible_update - self.step * self.rows


_MINUTE: Final = 60

_RRD_DEFAULT_ARCHIVES_FINEST_FIRST: Final = (
    _Archive(step=1 * _MINUTE, rows=2880),
    _Archive(step=5 * _MINUTE, rows=2880),
    _Archive(step=30 * _MINUTE, rows=4320),
    _Archive(step=360 * _MINUTE, rows=5840),
)


def expected_served_step(time_range: TimeRange, *, now: float) -> int:
    for archive in _RRD_DEFAULT_ARCHIVES_FINEST_FIRST:
        served_step = archive.served_step_for(time_range.step)
        widened = with_edge_neighbours(time_range, served_step)
        if archive.surely_reaches_back_to(widened.start, latest_possible_update=now):
            return served_step
    coarsest_archive = _RRD_DEFAULT_ARCHIVES_FINEST_FIRST[-1]
    return coarsest_archive.served_step_for(time_range.step)
