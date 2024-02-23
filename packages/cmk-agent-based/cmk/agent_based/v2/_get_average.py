#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import MutableMapping
from typing import Any, cast


def get_average(  # type: ignore[misc]
    value_store: MutableMapping[str, Any],
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

    This results in a so called "exponential moving average".

    The weight is chosen such that for long running timeseries the "backlog"
    (all recorded values in the last n minutes) will make up 50% of the
    weighted average.

    Assuming k values in the backlog, compute their combined weight such that
    they sum up to the backlog weight b (0.5 in our case):

       b = (1-w) ∑ᵢ₌₀ᵏ⁻¹  wⁱ  =>  w = (1 - b) ** (1/k)    ("geometric sum")

    For shorter timeseries we give the backlog more than those 50% weight
    with the advantages that

        * the initial value becomes irrelevant, and
        * for beginning timeseries we reach a meaningful value more quickly.

    Returns:

        The computed average

    """
    # Cast to avoid lots of mypy suppressions. It better reflects the tuth anyway.
    value_store = cast(MutableMapping[str, object], value_store)

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

    backlog_count = (backlog_minutes * 60.0) / time_diff

    relative_series_legth = (time - start_time) / (backlog_minutes * 60.0)
    # go back to regular EMA once the timeseries is twice   ↓ the backlog.
    # float**float is Any to mypy :-(
    backlog_weight = 0.5 ** min(1.0, relative_series_legth / 2.0)  # type: ignore[misc]

    weight: float = (1 - backlog_weight) ** (1.0 / backlog_count)  # type: ignore[misc]

    average = (1.0 - weight) * value + weight * last_average
    value_store[key] = (start_time, time, average)
    return average
