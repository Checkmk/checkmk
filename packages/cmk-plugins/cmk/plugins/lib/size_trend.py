#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import math
import time
from collections.abc import Mapping, MutableMapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckResult,
    get_rate,
    Metric,
    render,
    Result,
    State,
)

Levels = tuple[float, float]

MB = 1024 * 1024
SEC_PER_H = 60 * 60
SEC_PER_D = SEC_PER_H * 24


def _get_trend_average(
    value_store: MutableMapping[str, object],
    key: str,
    time: float,
    value: float,
    backlog_minutes: float,
    minimum_trend_minutes: float | None = None,
) -> float | None:
    """
    Attempt to calculate an exponential moving average, but when there is enough
    data to do so reasonably.

    NOTE: This function is NOT part of the public API and may change without
          notice.

    This function is a re-implementation/modified version of get_average, that
    tracks the number of measurements and returns None until there is enough
    data for a reliable trend prediction.

    Args:

        value_store:     The Mapping that holds the last value. Usually this will
                         be the value store provided by the API.
        key:             Unique ID for storing this average until the next check
        time:            Timestamp of new value
        value:           The new value
        backlog_minutes: Averaging horizon in minutes
        minimum_trend_minutes: Minimum number of minutes to wait since the
                         *first* sample has been collected, before we try to
                         show a trend. If None, defaults to backlog_minutes.

    Returns:

        The computed average if enough data has been collected. Otherwise, None.

    """
    if minimum_trend_minutes is None:
        minimum_trend_minutes = backlog_minutes

    match value_store.get(key, ()):
        case (
            float() | int() as start_time,
            float() | int() as last_time,
            float() | int() as last_average,
        ):
            pass
        case _other:
            value_store[key] = (time, time, value)
            return None

    time_since_starting_averaging = time - start_time

    # at the current rate, how many values are in the backlog?
    if (time_diff := time - last_time) <= 0:
        # Gracefully handle time-anomaly of target systems
        if time_since_starting_averaging >= minimum_trend_minutes * 60:
            return last_average
        else:
            return None

    if backlog_minutes * 60.0 < time_since_starting_averaging:
        backlog_count = (backlog_minutes * 60.0) / time_diff
    else:
        backlog_count = time_since_starting_averaging / time_diff

    backlog_weight = 0.5
    weight: float = (1 - backlog_weight) ** (1.0 / backlog_count)

    average = (1.0 - weight) * value + weight * last_average
    value_store[key] = (start_time, time, average)

    if time_since_starting_averaging >= minimum_trend_minutes * 60:
        return average

    return None


def _level_bytes_to_mb(levels: Levels | None) -> Levels | None:
    """convert levels given as bytes to levels as MB
    >>> _level_bytes_to_mb(None)
    >>> _level_bytes_to_mb((1048576, 2097152))
    (1.0, 2.0)
    """
    if levels is None:
        return None
    return levels[0] / MB, levels[1] / MB


def _reverse_level_signs(levels: Levels | None) -> Levels | None:
    """reverse the sign of all values
    >>> _reverse_level_signs(None)
    >>> _reverse_level_signs((-1, 2))
    (1, -2)
    """
    if levels is None:
        return None
    return -levels[0], -levels[1]


def size_trend(
    *,
    value_store: MutableMapping[str, Any],
    value_store_key: str,
    resource: str,
    levels: Mapping[str, Any],
    used_mb: float,
    size_mb: float,
    timestamp: float | None,
) -> CheckResult:
    """Trend computation for size related checks of disks

    Trends are computed in two steps. In the first step the delta to
    the last check is computed, using a normal check_mk counter.
    In the second step an average over that counter is computed to
    make a long-term prediction.

    Note:
      This function is experimental and may change in future releases.
      Use at your own risk!

    Args:
      value_store: Retrived value_store by calling check function
      value_store_key (str): The key (prefix) to use in the value_store
      resource (str): The resource in question, e.g. "disk", "ram", "swap".
      levels (dict): Level parameters for the trend computation. Items:
          "trend_range"          : 24,       # interval for the trend in hours
          "trend_perfdata"       : True      # generate perfomance data for trends
          "trend_bytes"          : (10, 20), # change during trend_range
          "trend_shrinking_bytes": (16, 32), # Bytes of shrinking during trend_range
          "trend_perc"           : (1, 2),   # percent change during trend_range
          "trend_shrinking_perc" : (1, 2),   # percent decreasing change during trend_range
          "trend_timeleft"       : (72, 48)  # time left in hours until full
          "trend_showtimeleft    : True      # display time left in infotext
        The item "trend_range" is required. All other items are optional.
      timestamp (float, optional): Time in secs used to calculate the rate
        and average. Defaults to "None".
      used_mb (float): Used space in MB.
      size_mb (float): Max. available space in MB.

    Yields:
      Result- and Metric- instances for the trend computation.
    """
    if (range_levels := levels.get("trend_range")) is None:
        return

    range_sec = range_levels * SEC_PER_H
    timestamp = timestamp or time.time()

    mb_per_sec = get_rate(value_store, "%s.delta" % value_store_key, timestamp, used_mb)

    avg_mb_per_sec = _get_trend_average(
        value_store=value_store,
        key="%s.trend" % value_store_key,
        time=timestamp,
        value=mb_per_sec,
        backlog_minutes=range_sec // 60,
    )

    if avg_mb_per_sec is None:
        yield Result(state=State.OK, summary="Not enough data to calculate trend")
        return

    mb_in_range = avg_mb_per_sec * range_sec

    if levels.get("trend_perfdata"):
        yield Metric("growth", mb_per_sec * SEC_PER_D)  # MB / day

    # apply levels for absolute growth in MB / interval
    yield from check_levels_v1(
        mb_in_range * MB,
        levels_upper=levels.get("trend_bytes"),
        levels_lower=_reverse_level_signs(levels.get("trend_shrinking_bytes")),
        # Don't use render.disksize here, see SUP-19150.
        render_func=lambda x: ("+" if x >= 0 else "") + render.bytes(x),
        label="trend per %s" % render.timespan(range_sec),
    )

    # apply levels for percentual growth in % / interval
    yield from check_levels_v1(
        mb_in_range * 100 / size_mb,
        levels_upper=levels.get("trend_perc"),
        levels_lower=_reverse_level_signs(levels.get("trend_shrinking_perc")),
        render_func=lambda x: ("+" if x >= 0 else "") + render.percent(x),
        label="trend per %s" % render.timespan(range_sec),
    )

    def to_abs(levels: Levels | None) -> Levels | None:
        if levels is None:
            return None
        return levels[0] / 100 * size_mb, levels[1] / 100 * size_mb

    def mins(levels1: Levels | None, levels2: Levels | None) -> Levels | None:
        return (
            (min(levels1[0], levels2[0]), min(levels1[1], levels2[1]))
            if levels1 and levels2
            else levels1 or levels2 or None  #
        )

    if levels.get("trend_perfdata"):
        yield Metric(
            "trend",
            avg_mb_per_sec * SEC_PER_D,
            levels=mins(
                _level_bytes_to_mb(levels.get("trend_bytes")),
                to_abs(levels.get("trend_perc")),
            ),
        )

    # CMK-13217: size_mb - used_mb < 0: the device reported nonsense, resulting in a crash:
    # ValueError("Cannot render negative timespan")
    free_space = max(size_mb - used_mb, 0)

    if mb_in_range > 0 and not math.isinf(value := free_space / mb_in_range):
        hours_till_full = value * range_sec / SEC_PER_H
        # Ignore time left if it's more than 10 years
        if hours_till_full > 10 * 365 * 24:
            return
        yield from check_levels_v1(
            hours_till_full,
            levels_lower=levels.get("trend_timeleft"),
            metric_name="trend_hoursleft" if "trend_showtimeleft" in levels else None,
            render_func=lambda x: render.timespan(x * SEC_PER_H),
            label="Time left until %s full" % resource,
        )
