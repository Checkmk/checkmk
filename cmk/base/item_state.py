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

import os
import traceback
from typing import Any, AnyStr, Dict, List, Optional, Tuple, Union

import cmk.utils.cleanup
import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.exceptions import MKException, MKGeneralException
from cmk.utils.type_defs import HostName
from cmk.utils.log import logger

# Constants for counters
SKIP = None
RAISE = False
ZERO = 0.0

g_last_counter_wrap: 'Optional[MKCounterWrapped]' = None
g_suppress_on_wrap = True  # Suppress check on wrap (raise an exception)
# e.g. do not suppress this check on check_mk -nv

ItemStateKeyElement = Optional[AnyStr]
ItemStateKey = Tuple[ItemStateKeyElement, ...]
ItemStates = Dict[ItemStateKey, Any]
OnWrap = Union[None, bool, float]


class MKCounterWrapped(MKException):
    pass


class CachedItemStates:
    def __init__(self) -> None:
        self._logger = logger
        super(CachedItemStates, self).__init__()
        self.reset()

    def reset(self) -> None:
        self._item_states: ItemStates = {}
        self._item_state_prefix: ItemStateKey = ()
        # timestamp of last modification
        self._last_mtime: Optional[float] = None
        self._removed_item_state_keys: List[ItemStateKey] = []
        self._updated_item_states: ItemStates = {}

    def clear_all_item_states(self) -> None:
        removed_item_state_keys = list(self._item_states.keys())
        self.reset()
        self._removed_item_state_keys = removed_item_state_keys

    def load(self, hostname: HostName) -> None:
        self._logger.debug("Loading item states")
        filename = cmk.utils.paths.counters_dir + "/" + hostname
        try:
            # TODO: refactoring. put these two values into a named tuple
            self._item_states = store.load_object_from_file(
                filename,
                default={},
                lock=True,
            )
            self._last_mtime = os.stat(filename).st_mtime
        finally:
            store.release_lock(filename)

    # TODO: self._last_mtime needs be updated accordingly after the save_object_to_file operation
    #       right now, the current mechanism is sufficient enough, since the save() function is only
    #       called as the final operation, just before the lifecycle of the CachedItemState ends
    def save(self, hostname: HostName) -> None:
        """ The job of the save function is to update the item state on disk.
        It simply returns, if it detects that the data wasn't changed at all since the last loading
        If the data on disk has been changed in the meantime, the cached data is updated from disk.
        Afterwards only the actual modifications (update/remove) are applied to the updated cached
        data before it is written back to disk.
        """
        self._logger.debug("Saving item states")
        filename = cmk.utils.paths.counters_dir + "/" + hostname
        if not self._removed_item_state_keys and not self._updated_item_states:
            return

        try:
            if not os.path.exists(cmk.utils.paths.counters_dir):
                os.makedirs(cmk.utils.paths.counters_dir)

            store.aquire_lock(filename)
            last_mtime = os.stat(filename).st_mtime
            if last_mtime != self._last_mtime:
                self._item_states = store.load_object_from_file(filename, default={})

                # Remove obsolete keys
                for key in self._removed_item_state_keys:
                    try:
                        del self._item_states[key]
                    except KeyError:
                        pass

                # Add updated keys
                self._item_states.update(self._updated_item_states)

            store.save_object_to_file(filename, self._item_states, pretty=False)
        except Exception:
            raise MKGeneralException("Cannot write to %s: %s" % (filename, traceback.format_exc()))
        finally:
            store.release_lock(filename)

    def clear_item_state(self, user_key: str) -> None:
        key = self.get_unique_item_state_key(user_key)
        self.remove_full_key(key)

    def clear_item_states_by_full_keys(self, full_keys: List[ItemStateKey]) -> None:
        for key in full_keys:
            self.remove_full_key(key)

    def remove_full_key(self, full_key: ItemStateKey) -> None:
        try:
            self._removed_item_state_keys.append(full_key)
            del self._item_states[full_key]
        except KeyError:
            pass

    def get_item_state(self, user_key: str, default: Any = None) -> Any:
        key = self.get_unique_item_state_key(user_key)
        return self._item_states.get(key, default)

    def set_item_state(self, user_key: str, state: Any) -> None:
        key = self.get_unique_item_state_key(user_key)
        self._item_states[key] = state
        self._updated_item_states[key] = state

    def get_all_item_states(self) -> ItemStates:
        return self._item_states

    def get_item_state_prefix(self) -> ItemStateKey:
        return self._item_state_prefix

    def set_item_state_prefix(self, args: ItemStateKey) -> None:
        self._item_state_prefix = args

    def get_unique_item_state_key(self, user_key: str) -> ItemStateKey:
        return self._item_state_prefix + (user_key,)


_cached_item_states = CachedItemStates()


def load(hostname: HostName) -> None:
    _cached_item_states.reset()
    _cached_item_states.load(hostname)


def save(hostname: HostName) -> None:
    _cached_item_states.save(hostname)


def set_item_state(user_key: str, state: Any) -> None:
    """Store arbitrary values until the next execution of a check.

    The user_key is the identifier of the stored value and needs
    to be unique per service."""
    _cached_item_states.set_item_state(user_key, state)


def get_item_state(user_key: str, default: Any = None) -> Any:
    """Returns the currently stored item with the user_key.

    Returns None or the given default value in case there
    is currently no such item stored."""
    return _cached_item_states.get_item_state(user_key, default)


def get_all_item_states() -> ItemStates:
    """Returns all stored items of the host that is currently being checked."""
    return _cached_item_states.get_all_item_states()


def clear_item_state(user_key: str) -> None:
    """Deletes a stored matching the given key. This needs to be
    the same key as used with set_item_state().

    In case the given item does not exist, the function returns
    without modification."""
    _cached_item_states.clear_item_state(user_key)


def clear_item_states_by_full_keys(full_keys: List[ItemStateKey]) -> None:
    """Clears all stored items specified in full_keys.

    The items are deleted by their full identifiers, not only the
    names specified with set_item_state(). For checks this is
    normally (<check_plugin_name>, <item>, <user_key>).
    """
    _cached_item_states.clear_item_states_by_full_keys(full_keys)


def cleanup_item_states() -> None:
    """Clears all stored items of the host that is currently being checked."""
    _cached_item_states.clear_all_item_states()


def set_item_state_prefix(*args: ItemStateKeyElement) -> None:
    _cached_item_states.set_item_state_prefix(args)


def get_item_state_prefix() -> ItemStateKey:
    return _cached_item_states.get_item_state_prefix()


def _unique_item_state_key(user_key: str) -> None:
    _cached_item_states.get_unique_item_state_key(user_key)


def continue_on_counter_wrap() -> None:
    global g_suppress_on_wrap
    g_suppress_on_wrap = False


# Idea (2): Checkmk should fetch a time stamp for each info. This should also be
# available as a global variable, so that this_time would be an optional argument.
def get_rate(user_key: str,
             this_time: float,
             this_val: float,
             allow_negative: bool = False,
             onwrap: OnWrap = SKIP,
             is_rate: bool = False) -> float:
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
def _get_counter(countername: str,
                 this_time: float,
                 this_val: float,
                 allow_negative: bool = False,
                 is_rate: bool = False) -> Tuple[float, float]:
    old_state = get_item_state(countername, None)
    set_item_state(countername, (this_time, this_val))

    # First time we see this counter? Do not return
    # any data!
    if old_state is None:
        if not g_suppress_on_wrap:
            return 1.0, 0.0
        raise MKCounterWrapped('Counter initialization')

    last_time, last_val = old_state
    timedif = this_time - last_time
    if timedif <= 0:  # do not update counter
        if not g_suppress_on_wrap:
            return 1.0, 0.0
        raise MKCounterWrapped('No time difference')

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
        raise MKCounterWrapped('Value overflow')

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


def get_average(itemname: str,
                this_time: float,
                this_val: float,
                backlog_minutes: float,
                initialize_zero: bool = True) -> float:
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
    last_time, last_average = get_item_state(itemname, (this_time, None))
    # first call: take current value as average or assume 0.0
    if last_average is None:
        average = 0.0 if initialize_zero else this_val
        set_item_state(itemname, (this_time, average))
        return average

    # at the current rate, how many values are in the backlog?
    time_diff = this_time - last_time
    if time_diff <= 0:
        # Gracefully handle time-anomaly of target systems
        return last_average
    backlog_count = (backlog_minutes * 60.) / time_diff

    backlog_weight = 0.50
    # TODO: For the version in the new Check API change the above line to
    # backlog_weight = 0.5 ** min(1, (time - start_time) / (2 * backlog_minutes * 60.)
    # And add to doc string:
    #  For shorter timeseries we give the backlog more than those 50% weight
    #  with the advantage that a) the initial value becomes irrelevant, and
    #  b) for beginning timeseries we reach a meaningful value more quickly.

    weight = (1 - backlog_weight)**(1.0 / backlog_count)

    average = (1.0 - weight) * this_val + weight * last_average
    set_item_state(itemname, (this_time, average))
    return average


cmk.utils.cleanup.register_cleanup(cleanup_item_states)
