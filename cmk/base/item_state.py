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

from contextlib import contextmanager
from pathlib import Path
import traceback
from typing import (
    Any,
    Callable,
    Dict,
    Final,
    Generator,
    Iterable,
    Iterator,
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
from cmk.utils.type_defs import HostName, Item
from cmk.utils.log import logger

# Constants for counters
SKIP = None
RAISE = False
ZERO = 0.0

g_last_counter_wrap: 'Optional[MKCounterWrapped]' = None
g_suppress_on_wrap = True  # Suppress check on wrap (raise an exception)
# e.g. do not suppress this check on check_mk -nv

_PluginName = str
# consider using ServiceID some day (Tuple[CheckPluginName, Item]]):
ServicePrefix = Tuple[_PluginName, Item]
_UserKey = str
_ValueStoreKey = Tuple[_PluginName, Item, _UserKey]
_OnWrap = Union[None, bool, float]


class _DynamicValueStore(Dict[_ValueStoreKey, Any]):
    """Represents the values that have been changed in a session

    This is a dict derivat that remembers if a key has been
    removed (having been removed is not the same as just not
    being in the dict at the moment!)
    """
    def __init__(self):
        super().__init__()
        self._removed_keys: Set[_ValueStoreKey] = set()

    @property
    def removed_keys(self) -> Set[_ValueStoreKey]:
        return self._removed_keys

    def __setitem__(self, key: _ValueStoreKey, value: Any) -> None:
        self._removed_keys.discard(key)
        super().__setitem__(key, value)

    def __delitem__(self, key: _ValueStoreKey) -> None:
        self._removed_keys.add(key)
        super().__delitem__(key)

    def pop(self, key: _ValueStoreKey, *args: Any) -> Any:
        self._removed_keys.add(key)
        return super().pop(key, *args)


class _StaticValueStore(Mapping[_ValueStoreKey, Any]):
    """Represents the values stored on disk"""

    STORAGE_PATH = Path(cmk.utils.paths.counters_dir)

    def __init__(self, host_name: HostName, log_debug: Callable[[str], None]) -> None:
        self._path: Final = self.STORAGE_PATH / host_name
        self._loaded_mtime: Optional[float] = None
        self._data: Mapping[_ValueStoreKey, Any] = {}
        self._log_debug = log_debug

    def __getitem__(self, key: _ValueStoreKey) -> Any:
        return self._data.__getitem__(key)

    def __iter__(self) -> Iterator[_ValueStoreKey]:
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
        removed: Set[_ValueStoreKey],
        updated: Mapping[_ValueStoreKey, Any],
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
                **updated,
            }
            store.save_object_to_file(self._path, data, pretty=False)
            self._mtime = self._path.stat().st_mtime
            self._data = data
        except Exception:
            raise MKGeneralException(f"Cannot write to {self._path}: {traceback.format_exc()}")
        finally:
            store.release_lock(self._path)


class _EffectiveValueStore(MutableMapping[_ValueStoreKey, Any]):  # pylint: disable=too-many-ancestors
    """Implements the overlay logic between dynamic and static value store"""
    def __init__(
        self,
        *,
        dynamic: _DynamicValueStore,
        static: _StaticValueStore,
    ) -> None:
        self._dynamic = dynamic
        self.static = static

    def _keys(self) -> Set[_ValueStoreKey]:
        return {
            k for k in (set(self._dynamic) | set(self.static))
            if k not in self._dynamic.removed_keys
        }

    def __getitem__(self, key: _ValueStoreKey) -> Any:
        if key in self._dynamic.removed_keys:
            raise KeyError(key)
        try:
            return self._dynamic.__getitem__(key)
        except KeyError:
            return self.static.__getitem__(key)

    def __delitem__(self, key: _ValueStoreKey) -> None:
        if key in self._dynamic.removed_keys:
            raise KeyError(key)
        try:
            self._dynamic.__delitem__(key)
            # key is now marked as removed.
        except KeyError:
            _ = self.static[key]

    def pop(self, key: _ValueStoreKey, *args: Any) -> Any:
        try:
            return self._dynamic.pop(key)
            # key is now marked as removed.
        except KeyError:
            return self.static.get(key, *args)

    def __setitem__(self, key: _ValueStoreKey, value: Any) -> None:
        self._dynamic.__setitem__(key, value)

    def __iter__(self) -> Iterator[_ValueStoreKey]:
        return iter(self._keys())

    def __len__(self) -> int:
        return len(self._keys())

    def commit(self) -> None:
        self.static.store(
            removed=self._dynamic.removed_keys,
            updated=self._dynamic,
        )
        self._dynamic = _DynamicValueStore()


class MKCounterWrapped(MKException):
    pass


class CachedItemStates:
    def __init__(self, host_name: HostName) -> None:
        self.host_name: Final = host_name
        self._logger = logger
        self._value_store = _EffectiveValueStore(
            dynamic=_DynamicValueStore(),
            static=_StaticValueStore(host_name, logger.debug),
        )
        self._item_state_prefix: Optional[ServicePrefix] = None

    def load(self) -> None:
        self._value_store.static.load()

    def save(self) -> None:
        if isinstance(self._value_store, _EffectiveValueStore):
            self._value_store.commit()

    def clear_item_state(self, user_key: _UserKey) -> None:
        key = self.get_unique_item_state_key(user_key)
        self.remove_full_key(key)

    def clear_item_states_by_full_keys(self, full_keys: Iterable[_ValueStoreKey]) -> None:
        for key in full_keys:
            self.remove_full_key(key)

    def remove_full_key(self, full_key: _ValueStoreKey) -> None:
        self._value_store.pop(full_key, None)

    def get_item_state(self, user_key: _UserKey, default: Any = None) -> Any:
        key = self.get_unique_item_state_key(user_key)
        return self._value_store.get(key, default)

    def set_item_state(self, user_key: _UserKey, state: Any) -> None:
        self._value_store[self.get_unique_item_state_key(user_key)] = state

    def get_all_item_states(self) -> MutableMapping[_ValueStoreKey, Any]:
        return dict(self._value_store.items())

    def get_item_state_prefix(self) -> Optional[ServicePrefix]:
        return self._item_state_prefix

    def set_item_state_prefix(self, args: Optional[ServicePrefix]) -> None:
        self._item_state_prefix = args

    def get_unique_item_state_key(self, user_key: _UserKey) -> _ValueStoreKey:
        if self._item_state_prefix is None:
            # TODO: consolidate this with the exception thrown in value_store.py
            raise MKGeneralException("accessing item state outside check function")
        return self._item_state_prefix + (user_key,)


_host_value_stores: MutableMapping[HostName, CachedItemStates] = {}

_cached_item_states: Optional[CachedItemStates] = None


def _get_cached_item_states() -> CachedItemStates:
    if _cached_item_states is None:
        raise MKGeneralException("no item states have been loaded")
    return _cached_item_states


@contextmanager
def load_host_value_store(
    host_name: HostName,
    *,
    store_changes: bool,
) -> Generator[CachedItemStates, None, None]:
    """Select (or create) the correct value store for the host and (re)load it"""
    global _cached_item_states

    pushed_host_name = _cached_item_states.host_name if _cached_item_states else None

    if not store_changes:
        _cached_item_states = CachedItemStates(host_name)
    else:
        try:
            _cached_item_states = _host_value_stores[host_name]
        except KeyError:
            _cached_item_states = _host_value_stores.setdefault(
                host_name,
                CachedItemStates(host_name),
            )

    assert _cached_item_states is not None

    _cached_item_states.load()
    try:
        yield _cached_item_states
        if store_changes:
            _cached_item_states.save()
    finally:
        _cached_item_states = _host_value_stores.get(pushed_host_name) if pushed_host_name else None


def set_item_state(user_key: _UserKey, state: Any) -> None:
    """Store arbitrary values until the next execution of a check.

    The user_key is the identifier of the stored value and needs
    to be unique per service."""
    _get_cached_item_states().set_item_state(user_key, state)


def get_item_state(user_key: _UserKey, default: Any = None) -> Any:
    """Returns the currently stored item with the user_key.

    Returns None or the given default value in case there
    is currently no such item stored."""
    return _get_cached_item_states().get_item_state(user_key, default)


def get_all_item_states() -> Mapping[_ValueStoreKey, Any]:
    """Returns all stored items of the host that is currently being checked."""
    return _get_cached_item_states().get_all_item_states()


def clear_item_state(user_key: _UserKey) -> None:
    """Deletes a stored matching the given key. This needs to be
    the same key as used with set_item_state().

    In case the given item does not exist, the function returns
    without modification."""
    _get_cached_item_states().clear_item_state(user_key)


def clear_item_states_by_full_keys(full_keys: Iterable[_ValueStoreKey]) -> None:
    """Clears all stored items specified in full_keys.

    The items are deleted by their full identifiers, not only the
    names specified with set_item_state(). For checks this is
    normally (<check_plugin_name>, <item>, <user_key>).
    """
    _get_cached_item_states().clear_item_states_by_full_keys(full_keys)


# TODO: drop this, and pass the active CachedItemStates to the callsite!
def set_item_state_prefix(args: Optional[ServicePrefix]) -> None:
    _get_cached_item_states().set_item_state_prefix(args)


# TODO: drop this, and pass the active CachedItemStates to the callsite!
def get_item_state_prefix() -> Optional[ServicePrefix]:
    return _get_cached_item_states().get_item_state_prefix()


def continue_on_counter_wrap() -> None:
    """Make get_rate always return 0 if something goes wrong"""
    global g_suppress_on_wrap
    g_suppress_on_wrap = False


# Idea (2): Checkmk should fetch a time stamp for each info. This should also be
# available as a global variable, so that this_time would be an optional argument.
def get_rate(user_key: _UserKey,
             this_time: float,
             this_val: float,
             allow_negative: bool = False,
             onwrap: _OnWrap = SKIP,
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
def _get_counter(countername: _UserKey,
                 this_time: float,
                 this_val: float,
                 allow_negative: bool = False,
                 is_rate: bool = False) -> Tuple[float, float]:
    old_state = _get_cached_item_states().get_item_state(countername, None)
    _get_cached_item_states().set_item_state(countername, (this_time, this_val))

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


def get_average(itemname: _UserKey,
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
    cached_item_states = _get_cached_item_states()
    last_time, last_average = cached_item_states.get_item_state(itemname, (this_time, None))
    # first call: take current value as average or assume 0.0
    if last_average is None:
        average = 0.0 if initialize_zero else this_val
        cached_item_states.set_item_state(itemname, (this_time, average))
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
    cached_item_states.set_item_state(itemname, (this_time, average))
    return average
