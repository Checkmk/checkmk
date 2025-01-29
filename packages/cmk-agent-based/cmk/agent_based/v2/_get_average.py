#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import MutableMapping


def get_average(
    value_store: MutableMapping[str, object],
    key: str,
    time: float,
    value: float,
    backlog_minutes: float,
) -> float:
    """Return new average based on current value and last average

    Args:

        value_store:     The Mapping that holds the last value. Usually this will
                         be the value store provided by the API.
        key:             Unique ID for storing this average until the next check
        time:            Timestamp of new value
        value:           The new value
        backlog_minutes: Averaging horizon in minutes

    This function returns the new average value aₙ as the weighted sum of the
    current value xₙ and the last average:

        aₙ = (1 - w)xₙ + waₙ₋₁

           = (1-w) ∑ᵢ₌₀ⁿ wⁱxₙ₋ᵢ

    This results in a so-called "exponential moving average".

    The weight is chosen such that for long-running timeseries the "backlog"
    (all recorded values in the last n minutes) will make up 50% of the
    weighted average.

    Assuming k values in the backlog, compute their combined weight such that
    they sum up to the backlog weight b (0.5 in our case):

       b = (1-w) ∑ᵢ₌₀ᵏ⁻¹  wⁱ  =>  w = (1 - b) ** (1/k)    ("geometric sum")

    Until the averaging horizon has been reached, we set the horizon to
    the time passed since starting to average. This:

        * Avoids giving undue weight to the first value
        * Helps to arrive at a meaningful average more quickly

    Returns:

        The computed average

    """
    match value_store.get(key, ()):
        case (
            float() | int() as start_time,
            float() | int() as last_time,
            float() | int() as last_average,
        ):
            pass
        case _other:
            value_store[key] = (time, time, value)
            return value

    # at the current rate, how many values are in the backlog?
    if (time_diff := time - last_time) <= 0:
        # Gracefully handle time-anomaly of target systems
        return last_average

    time_since_starting_averaging = time - start_time
    if backlog_minutes * 60.0 < time_since_starting_averaging:
        backlog_count = (backlog_minutes * 60.0) / time_diff
    else:
        backlog_count = time_since_starting_averaging / time_diff

    backlog_weight = 0.5
    weight: float = (1 - backlog_weight) ** (1.0 / backlog_count)

    average = (1.0 - weight) * value + weight * last_average
    value_store[key] = (start_time, time, average)
    return average
