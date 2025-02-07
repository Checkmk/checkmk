#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper functions to work with persisted values"""

from collections.abc import MutableMapping
from typing import Any, cast

from ._checking_classes import IgnoreResultsError


class GetRateError(IgnoreResultsError):
    """The exception raised by :func:`.get_rate`.
    If unhandled, this exception will make the service go stale.
    """


def get_rate(  # type: ignore[explicit-any]
    value_store: MutableMapping[str, Any],
    key: str,
    time: float,
    value: float,
    *,
    raise_overflow: bool = False,
) -> float:
    """
    1. Update value store.
    2. Calculate rate based on current value and time and last value and time

    Args:

        value_store:     The mapping that holds the last value.
                         Usually this will be the value store provided by the APIs
                         :func:`get_value_store`.
        key:             Unique ID for storing the time/value pair until the next check
        time:            Timestamp of new value
        value:           The new value
        raise_overflow:  Raise a :class:`GetRateError` if the rate is negative

    This function returns the rate of a measurement rₙ as the quotient of the `value` and `time`
    provided to the current function call (xₙ, tₙ) and the `value` and `time` provided to the
    previous function call (xₙ₋₁, tₙ₋₁):

        rₙ = (xₙ - xₙ₋₁) / (tₙ - tₙ₋₁)

    Note that the function simply computes the quotient of the values and times given,
    regardless of any unit. You might as well pass something different than the time.
    However, this function is written with the use case of passing timestamps in mind.

    A :class:`GetRateError` will be raised if one of the following happens:

        * the function is called for the first time
        * the time has not changed
        * the rate is negative and `raise_overflow` is set to True (useful
          for instance when dealing with counters)

    In general there is no need to catch a :class:`.GetRateError`, as it
    inherits :class:`.IgnoreResultsError`.

    Example:

        >>> # in practice: my_store = get_value_store()
        >>> my_store = {}
        >>> try:
        ...     rate = get_rate(my_store, 'my_rate', 10, 23)
        ... except GetRateError:
        ...     pass  # this fails the first time, because my_store is empty.
        >>> my_store  # now remembers the last time/value
        {'my_rate': (10, 23)}
        >>> # Assume in the next check cycle (60 seconds later) the value has increased to 56.
        >>> # get_rate uses the new and old values to compute (56 - 23) / (70 - 10)
        >>> get_rate(my_store, 'my_rate', 70, 56)
        0.55

    Returns:

        The computed rate

    """
    # Cast to avoid lots of mypy suppressions. It better reflects the truth anyway.
    value_store = cast(MutableMapping[str, object], value_store)

    last_state = value_store.get(key)
    value_store[key] = (time, value)

    match last_state:
        case (
            float() | int() as last_time,
            float() | int() as last_value,
        ):
            pass
        case _other:
            raise GetRateError(
                f"Counter {key!r} has been initialized. Result available on second check execution."
            )

    if time <= last_time:
        raise GetRateError("No rate available (time anomaly detected)")

    rate = float(value - last_value) / (time - last_time)
    if raise_overflow and rate < 0:
        # Do not try to handle wrapped counters. We do not know
        # wether they are 32 or 64 bit. It also could happen counter
        # reset (reboot, etc.). Better is to leave this value undefined
        # and wait for the next check interval.
        raise GetRateError(f"Negative rate for {key!r}. Suspecting value overflow.")

    return rate


def get_average(  # type: ignore[explicit-any]
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
    # Cast to avoid lots of mypy suppressions. It better reflects the truth anyway.
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
