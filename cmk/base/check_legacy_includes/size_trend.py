#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

import time
from collections.abc import Callable

from cmk.agent_based.v2 import (
    get_average,
    get_rate,
    get_value_store,
    IgnoreResultsError,
    render,
)

# ==================================================================================================
# THESE FUNCTIONS DEFINED HERE ARE IN THE PROCESS OF OR HAVE ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THESE FUNCTIONS ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk.plugins.lib/size_trend.py
# ==================================================================================================

Levels = tuple[float, float]


def _check_shrinking(
    trend: float, levels: Levels | None, range_hours: float, renderer: Callable[..., str]
) -> tuple[int, str]:
    """test for negative trend
    >>> _check_shrinking(5, (1, 2), 7, lambda _: "foo")
    (0, '')
    >>> _check_shrinking(-5, None, 7, lambda _: "foo")
    (0, '')
    >>> _check_shrinking(-5, (1, 2), 7, lambda _: "foo")
    (2, 'shrinking too fast (warn/crit at foo/foo per 7.0 h)(!!)')
    """
    state, problem = 0, ""
    if levels is None:
        return state, problem

    wa, cr = levels
    if trend <= -wa:
        problem = f"shrinking too fast (warn/crit at {renderer(wa)}/{renderer(cr)} per {range_hours:.1f} h)(!"
        state = 1
        if trend <= -cr:
            state = 2
            problem += "!"
        problem += ")"
    return state, problem


def size_trend(
    check: str,
    item: str,
    resource: str,
    levels: dict,
    used_mb: float,
    size_mb: float,
    timestamp: float | None = None,
) -> tuple[int, str, list]:
    """Trend computation for size related checks of disks, ram, etc.
    Trends are computed in two steps. In the first step the delta to
    the last check is computed, using a normal check_mk counter.
    In the second step an average over that counter is computed to
    make a long-term prediction.

    Note:
      This function is experimental and may change in future releases.
      Use at your own risk!

    Args:
      check (str): The name of the check, e.g. "df".
      item (str): The name of the item, e.g. the mountpoint "/" for df.
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

    Returns:
      A tuple of (state, infotext, perfdata) for the trend computation.
      If a MKCounterWrapped occurs (i.e. there is not enough data
      present for the trend computation) the tuple (0, '', []) is
      returned.
    """
    value_store = get_value_store()

    perfdata: list[
        (  #
            tuple[str, float]
            | tuple[str, float, float | None, float | None, float | None, float | None]  #
        )
    ]
    state, infotext, perfdata, problems = 0, "", [], []

    MB = 1024.0 * 1024.0
    H24 = 60 * 60 * 24

    range_hours = levels["trend_range"]
    range_sec = range_hours * 3600.0
    if not timestamp:
        timestamp = time.time()

    # compute current rate in MB/s by computing delta since last check
    try:
        rate = get_rate(
            get_value_store(),
            f"{check}.{item}.delta",
            timestamp,
            used_mb,
        )
    except IgnoreResultsError:
        # need more data for computing a trend
        return 0, "", []

    if levels.get("trend_perfdata"):
        perfdata.append(("growth", rate * H24))

    # average trend in MB/s, initialized with zero (by default)
    rate_avg = get_average(value_store, f"{check}.{item}.trend", timestamp, rate, range_sec / 60.0)

    trend = rate_avg * range_sec
    sign = "+" if trend > 0 else ""
    infotext += f", trend: {sign}{render.bytes(trend * MB)} / {range_hours:g} hours"

    # levels for performance data
    warn_perf: float | None = None
    crit_perf: float | None = None

    # apply levels for absolute growth / interval
    trend_bytes = levels.get("trend_bytes")
    if trend_bytes:
        wa, cr = trend_bytes
        warn_perf, crit_perf = wa / MB, cr / MB
        if trend * MB >= wa:
            problems.append(
                "growing too fast (warn/crit at %s/%s per %.1f h)(!"
                % (
                    render.bytes(wa),
                    render.bytes(cr),
                    range_hours,
                )
            )
            state = max(1, state)
            if trend * MB >= cr:
                state = 2
                problems[-1] += "!"
            problems[-1] += ")"

    tmp_state, tmp_problem = _check_shrinking(
        trend * MB,
        levels.get("trend_shrinking_bytes"),
        range_hours,
        render.bytes,
    )
    if tmp_state > 0:
        state = max(state, tmp_state)
        problems.append(tmp_problem)

    # apply levels for growth relative to filesystem size
    trend_perc: tuple[float, float] | None = levels.get("trend_perc")
    if trend_perc:
        wa_perc, cr_perc = trend_perc
        wa = wa_perc / 100.0 * size_mb
        cr = cr_perc / 100.0 * size_mb
        if warn_perf is not None:
            assert crit_perf is not None
            warn_perf = min(warn_perf, wa)
            crit_perf = min(crit_perf, cr)
        else:
            warn_perf, crit_perf = wa, cr
        if trend >= wa:
            problems.append(
                "growing too fast (warn/crit at %s/%s per %.1f h)(!"
                % (
                    render.percent(wa_perc),
                    render.percent(cr_perc),
                    range_hours,
                )
            )
            state = max(1, state)
            if trend >= cr:
                state = 2
                problems[-1] += "!"
            problems[-1] += ")"

    tmp_state, tmp_problem = _check_shrinking(
        100 * trend / size_mb,
        levels.get("trend_shrinking_perc"),
        range_hours,
        render.percent,
    )
    if tmp_state > 0:
        state = max(state, tmp_state)
        problems.append(tmp_problem)

    # compute time until filesystem is full (only for positive trend, of course)

    # The start value of hours_left is negative. The pnp graph and the perfometer
    # will interpret this as inifinite -> not growing
    hours_left = -1
    if trend > 0:

        def format_hours(hours: float) -> str:
            if hours > 365 * 24:
                return "more than a year"
            elif hours > 90 * 24:
                return "%0d months" % (hours / (30 * 24))  # fixed: true-division
            elif hours > 4 * 7 * 24:  # 4 weeks
                return "%0d weeks" % (hours / (7 * 24))  # fixed: true-division
            elif hours > 7 * 24:  # 1 week
                return "%0.1f weeks" % (hours / (7 * 24))  # fixed: true-division
            elif hours > 2 * 24:  # 2 days
                return "%0.1f days" % (hours / 24)  # fixed: true-division
            return "%d hours" % hours

        # CMK-13217: size_mb - used_mb < 0: the device reported nonsense
        hours_left = max((size_mb - used_mb) / trend * range_hours, 0)
        hours_txt = format_hours(hours_left)

        timeleft = levels.get("trend_timeleft")
        if timeleft:
            wa, cr = timeleft
            if hours_left <= cr:
                state = 2
                problems.append(f"only {hours_txt} until {resource} full(!!)")
            elif hours_left <= wa:
                state = max(state, 1)
                problems.append(f"only {hours_txt} until {resource} full(!)")
            elif hours_left <= wa * 2 or levels.get("trend_showtimeleft"):
                problems.append(f"time left until {resource} full: {hours_txt}")
        elif levels.get("trend_showtimeleft"):
            problems.append(f"time left until {resource} full: {hours_txt}")

    if levels.get("trend_perfdata"):
        perfdata.append(
            (
                "trend",
                rate_avg * H24,
                (warn_perf / range_sec * H24) if warn_perf is not None else None,
                (crit_perf / range_sec * H24) if crit_perf is not None else None,
                0,
                1.0 * size_mb / range_hours,
            )
        )

    if levels.get("trend_showtimeleft"):
        perfdata.append(("trend_hoursleft", hours_left))

    if problems:
        infotext += " - %s" % ", ".join(problems)

    return state, infotext, perfdata
