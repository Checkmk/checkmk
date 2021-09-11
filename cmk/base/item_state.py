#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
These functions allow checks to keep a memory until the next time
the check is being executed. The most frequent use case is compu-
tation of rates from two succeeding counter values. This is done
via the helper function get_rate(). Averaging is another example
and done by get_average().

While a host is being checked this memory is kept in _cached_item_states.
That is a dictionary. The keys are unique to one check type and
item. The value is free form.

Note: The item state is kept in tmpfs and not reboot-persistant.
Do not store long-time things here. Also do not store complex
structures like log files or stuff.
"""

from typing import Any, Optional, Tuple, Union

from cmk.utils.exceptions import MKException

from cmk.base.api.agent_based.value_store import get_value_store

# Constants for counters
SKIP = None
RAISE = False
ZERO = 0.0

g_last_counter_wrap: "Optional[MKCounterWrapped]" = None
g_suppress_on_wrap = True  # Suppress check on wrap (raise an exception)
# e.g. do not suppress this check on check_mk -nv

_UserKey = str
_OnWrap = Union[None, bool, float]


class MKCounterWrapped(MKException):
    pass


def _stringify(user_key: object) -> _UserKey:
    """get a string representation of the key

    The old API never *enforced* usage of a string as key,
    so we use this function to keep weird legacy checks
    working.
    """
    return user_key if isinstance(user_key, _UserKey) else repr(user_key)


def set_item_state(user_key: object, state: Any) -> None:
    """Store arbitrary values until the next execution of a check.

    The user_key is the identifier of the stored value and needs
    to be unique per service."""
    get_value_store()[_stringify(user_key)] = state


def get_item_state(user_key: object, default: Any = None) -> Any:
    """Returns the currently stored item with the user_key.

    Returns None or the given default value in case there
    is currently no such item stored."""
    return get_value_store().get(_stringify(user_key), default)


def clear_item_state(user_key: _UserKey) -> None:
    """Deletes a stored matching the given key. This needs to be
    the same key as used with set_item_state().

    In case the given item does not exist, the function returns
    without modification."""
    get_value_store().pop(user_key, None)


def continue_on_counter_wrap() -> None:
    """Make get_rate always return 0 if something goes wrong"""
    global g_suppress_on_wrap
    g_suppress_on_wrap = False


# Idea (2): Checkmk should fetch a time stamp for each info. This should also be
# available as a global variable, so that this_time would be an optional argument.
def get_rate(
    user_key: _UserKey,
    this_time: float,
    this_val: float,
    allow_negative: bool = False,
    onwrap: _OnWrap = SKIP,
    is_rate: bool = False,
) -> float:
    try:
        return _get_counter(user_key, this_time, this_val, allow_negative, is_rate)[1]
    except MKCounterWrapped as e:
        if onwrap is RAISE:
            raise
        if onwrap is SKIP:
            global g_last_counter_wrap
            g_last_counter_wrap = e
            return 0.0
        return onwrap


# Helper for get_rate(). Note: this function has been part of the official check API
# for a long time. So we cannot change its call syntax or remove it for the while.
def _get_counter(
    countername: _UserKey,
    this_time: float,
    this_val: float,
    allow_negative: bool = False,
    is_rate: bool = False,
) -> Tuple[float, float]:
    old_state = get_item_state(countername, None)
    set_item_state(countername, (this_time, this_val))

    # First time we see this counter? Do not return
    # any data!
    if old_state is None:
        if not g_suppress_on_wrap:
            return 1.0, 0.0
        raise MKCounterWrapped("Counter initialization")

    last_time, last_val = old_state
    timedif = this_time - last_time
    if timedif <= 0:  # do not update counter
        if not g_suppress_on_wrap:
            return 1.0, 0.0
        raise MKCounterWrapped("No time difference")

    if not is_rate:
        valuedif = this_val - last_val
    else:
        valuedif = this_val

    if valuedif < 0 and not allow_negative:
        # Do not try to handle wrapper counters. We do not know
        # wether they are 32 or 64 bit. It also could happen counter
        # reset (reboot, etc.). Better is to leave this value undefined
        # and wait for the next check interval.
        if not g_suppress_on_wrap:
            return 1.0, 0.0
        raise MKCounterWrapped("Value overflow")

    per_sec = float(valuedif) / timedif
    return timedif, per_sec


def reset_wrapped_counters() -> None:
    global g_last_counter_wrap
    g_last_counter_wrap = None


# TODO: Can we remove this? (check API)
def last_counter_wrap() -> Optional[MKCounterWrapped]:
    return g_last_counter_wrap


def raise_counter_wrap() -> None:
    if g_last_counter_wrap:
        raise g_last_counter_wrap  # pylint: disable=raising-bad-type


def get_average(
    itemname: _UserKey,
    this_time: float,
    this_val: float,
    backlog_minutes: float,
    initialize_zero: bool = True,
) -> float:
    """Return new average based on current value and last average

    itemname        : unique ID for storing this average until the next check
    this_time       : timestamp of new value
    backlog         : averaging horizon in minutes
    initialize_zero : assume average of 0.0 when now previous average is stored

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
    """
    value_store = get_value_store()
    last_time, last_average = value_store.get(itemname, (this_time, None))
    # first call: take current value as average or assume 0.0
    if last_average is None:
        average = 0.0 if initialize_zero else this_val
        value_store[itemname] = (this_time, average)
        return average

    # at the current rate, how many values are in the backlog?
    time_diff = this_time - last_time
    if time_diff <= 0:
        # Gracefully handle time-anomaly of target systems
        return last_average
    backlog_count = (backlog_minutes * 60.0) / time_diff

    backlog_weight = 0.50
    # TODO: For the version in the new Check API change the above line to
    # backlog_weight = 0.5 ** min(1, (time - start_time) / (2 * backlog_minutes * 60.)
    # And add to doc string:
    #  For shorter timeseries we give the backlog more than those 50% weight
    #  with the advantage that a) the initial value becomes irrelevant, and
    #  b) for beginning timeseries we reach a meaningful value more quickly.

    weight = (1 - backlog_weight) ** (1.0 / backlog_count)

    average = (1.0 - weight) * this_val + weight * last_average
    value_store[itemname] = (this_time, average)
    return average
