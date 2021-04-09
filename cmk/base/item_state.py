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

from pathlib import Path
import traceback
from typing import (
    Any,
    Callable,
    Final,
    Iterator,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Set,
    Tuple,
    Union,
)

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

ItemStateKeyElement = Optional[str]
ItemStateKey = Tuple[ItemStateKeyElement, ...]
ItemStates = Mapping[ItemStateKey, Any]
MutableItemStates = MutableMapping[ItemStateKey, Any]
OnWrap = Union[None, bool, float]

# TODO: add _DynamicValueStore (values that have been changed in a session)


class _StaticValueStore(ItemStates):
    """Represents the values stored on disk"""

    STORAGE_PATH = Path(cmk.utils.paths.counters_dir)

    def __init__(self, host_name: HostName, log_debug: Callable) -> None:
        self._path: Final = self.STORAGE_PATH / host_name
        self._loaded_mtime: Optional[float] = None
        self._data: ItemStates = {}
        self._log_debug = log_debug

    def __getitem__(self, key: ItemStateKey) -> Any:
        return self._data.__getitem__(key)

    def __iter__(self) -> Iterator[ItemStateKey]:
        return self._data.__iter__()

    def __len__(self) -> int:
        return len(self._data)

    def load(self) -> None:
        self._log_debug("Loading item states")

        try:
            store.aquire_lock(self._path)
            self._load()
        finally:
            store.release_lock(self._path)

    def _load(self) -> None:
        try:
            current_mtime = self._path.stat().st_mtime
        except FileNotFoundError:
            return

        if current_mtime == self._loaded_mtime:
            self._log_debug("already loaded")
            return

        self._data = store.load_object_from_file(self._path, default={}, lock=False)
        self._loaded_mtime = current_mtime

    def store(
        self,
        *,
        removed: Set[ItemStateKey],
        updated: ItemStates,
    ) -> None:
        """Re-load and then store the changes of the item state to disk

        Make sure the object is in sync with the file after writing.
        """
        self._log_debug("Storing item states")
        if not (removed or updated):
            return

        self._path.parent.mkdir(parents=True, exist_ok=True)

        try:
            store.aquire_lock(self._path)
            self._load()

            data = {
                **{k: v for k, v in self._data.items() if k not in removed},
                **{k: v for k, v in updated.items() if k not in removed},
            }
            store.save_object_to_file(self._path, data, pretty=False)
            self._mtime = self._path.stat().st_mtime
            self._data = data
        except Exception:
            raise MKGeneralException(f"Cannot write to {self._path}: {traceback.format_exc()}")
        finally:
            store.release_lock(self._path)


class MKCounterWrapped(MKException):
    pass


class CachedItemStates:
    def __init__(self) -> None:
        self._logger = logger
        super(CachedItemStates, self).__init__()
        self.reset()

    def reset(self) -> None:
        self._item_state_prefix: Optional[ItemStateKey] = None
        self._static_values: Optional[_StaticValueStore] = None
        self._removed_item_state_keys: Set[ItemStateKey] = set()
        self._updated_item_states: MutableItemStates = {}

    def load(self, hostname: HostName) -> None:
        self._static_values = _StaticValueStore(hostname, logger.debug)
        self._static_values.load()

    def save(self) -> None:
        if self._static_values is None:
            return
        self._static_values.store(
            removed=self._removed_item_state_keys,
            updated=self._updated_item_states,
        )

    def clear_item_state(self, user_key: str) -> None:
        key = self.get_unique_item_state_key(user_key)
        self.remove_full_key(key)

    def clear_item_states_by_full_keys(self, full_keys: List[ItemStateKey]) -> None:
        for key in full_keys:
            self.remove_full_key(key)

    def remove_full_key(self, full_key: ItemStateKey) -> None:
        self._removed_item_state_keys.add(full_key)

    def get_item_state(self, user_key: str, default: Any = None) -> Any:
        key = self.get_unique_item_state_key(user_key)
        if key in self._removed_item_state_keys:
            return default
        try:
            return self._lookup(key)
        except KeyError:
            return default

    def _lookup(self, key: ItemStateKey) -> Any:
        try:
            return self._updated_item_states[key]
        except KeyError:
            if self._static_values is None:
                # TODO: refactor s.t. this can never happen.
                raise
            return self._static_values[key]

    def set_item_state(self, user_key: str, state: Any) -> None:
        key = self.get_unique_item_state_key(user_key)
        self._removed_item_state_keys.discard(key)
        self._updated_item_states[key] = state

    def get_all_item_states(self) -> MutableItemStates:
        if self._static_values is None:
            # TODO: refactor s.t. this can never happen.
            return {
                k: v
                for k, v in self._updated_item_states.items()
                if k not in self._removed_item_state_keys
            }
        keys = (set(self._static_values) |
                set(self._updated_item_states)) - self._removed_item_state_keys
        return {k: self._lookup(k) for k in keys}

    def get_item_state_prefix(self) -> Optional[ItemStateKey]:
        return self._item_state_prefix

    def set_item_state_prefix(self, args: Optional[ItemStateKey]) -> None:
        self._item_state_prefix = args

    def get_unique_item_state_key(self, user_key: str) -> ItemStateKey:
        if self._item_state_prefix is None:
            # TODO: consolidate this with the exception thrown in value_store.py
            raise MKGeneralException("accessing item state outside check function")
        return self._item_state_prefix + (user_key,)


_cached_item_states = CachedItemStates()


def load(hostname: HostName) -> None:
    _cached_item_states.load(hostname)


def save() -> None:
    _cached_item_states.save()


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
    _cached_item_states.reset()


def set_item_state_prefix(args: Optional[ItemStateKey]) -> None:
    _cached_item_states.set_item_state_prefix(args)


def get_item_state_prefix() -> Optional[ItemStateKey]:
    return _cached_item_states.get_item_state_prefix()


def _unique_item_state_key(user_key: str) -> None:
    _cached_item_states.get_unique_item_state_key(user_key)


def continue_on_counter_wrap() -> None:
    """Make get_rate always return 0 if something goes wrong"""
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
