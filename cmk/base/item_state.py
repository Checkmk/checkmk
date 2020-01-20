#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
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
from typing import AnyStr, Union, List, Optional, Dict, Any, Tuple  # pylint: disable=unused-import

import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.exceptions import (
    MKException,
    MKGeneralException,
)
from cmk.utils.type_defs import HostName  # pylint: disable=unused-import

import cmk.base.cleanup

# Constants for counters
SKIP = None
RAISE = False
ZERO = 0.0

g_last_counter_wrap = None  # type: Optional[MKCounterWrapped]
g_suppress_on_wrap = True  # Suppress check on wrap (raise an exception)
# e.g. do not suppress this check on check_mk -nv

ItemStateKeyElement = Optional[AnyStr]
ItemStateKey = Tuple[ItemStateKeyElement, ...]
ItemStates = Dict[ItemStateKey, Any]
OnWrap = Union[None, bool, float]


class MKCounterWrapped(MKException):
    pass


class CachedItemStates(object):
    def __init__(self):
        # type: () -> None
        super(CachedItemStates, self).__init__()
        self.reset()

    def reset(self):
        # type: () -> None
        self._item_states = {}  # type: ItemStates
        self._item_state_prefix = ()  # type: ItemStateKey
        # timestamp of last modification
        self._last_mtime = None  # type: Optional[float]
        self._removed_item_state_keys = []  # type: List[ItemStateKey]
        self._updated_item_states = {}  # type: ItemStates

    def clear_all_item_states(self):
        # type: () -> None
        removed_item_state_keys = list(self._item_states.keys())
        self.reset()
        self._removed_item_state_keys = removed_item_state_keys

    def load(self, hostname):
        # type: (HostName) -> None
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
    def save(self, hostname):
        # type: (HostName) -> None
        """ The job of the save function is to update the item state on disk.
        It simply returns, if it detects that the data wasn't changed at all since the last loading
        If the data on disk has been changed in the meantime, the cached data is updated from disk.
        Afterwards only the actual modifications (update/remove) are applied to the updated cached
        data before it is written back to disk.
        """
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

    def clear_item_state(self, user_key):
        # type: (str) -> None
        key = self.get_unique_item_state_key(user_key)
        self.remove_full_key(key)

    def clear_item_states_by_full_keys(self, full_keys):
        # type: (List[ItemStateKey]) -> None
        for key in full_keys:
            self.remove_full_key(key)

    def remove_full_key(self, full_key):
        # type: (ItemStateKey) -> None
        try:
            self._removed_item_state_keys.append(full_key)
            del self._item_states[full_key]
        except KeyError:
            pass

    def get_item_state(self, user_key, default=None):
        # type: (str, Any) -> Any
        key = self.get_unique_item_state_key(user_key)
        return self._item_states.get(key, default)

    def set_item_state(self, user_key, state):
        # type: (str, Any) -> None
        key = self.get_unique_item_state_key(user_key)
        self._item_states[key] = state
        self._updated_item_states[key] = state

    def get_all_item_states(self):
        # type: () -> ItemStates
        return self._item_states

    def get_item_state_prefix(self):
        # type: () -> ItemStateKey
        return self._item_state_prefix

    def set_item_state_prefix(self, args):
        # type: (ItemStateKey) -> None
        self._item_state_prefix = args

    def get_unique_item_state_key(self, user_key):
        # type: (str) -> ItemStateKey
        return self._item_state_prefix + (user_key,)


_cached_item_states = CachedItemStates()


def load(hostname):
    # type: (HostName) -> None
    _cached_item_states.reset()
    _cached_item_states.load(hostname)


def save(hostname):
    # type: (HostName) -> None
    _cached_item_states.save(hostname)


def set_item_state(user_key, state):
    # type: (str, Any) -> None
    """Store arbitrary values until the next execution of a check.

    The user_key is the identifier of the stored value and needs
    to be unique per service."""
    _cached_item_states.set_item_state(user_key, state)


def get_item_state(user_key, default=None):
    # type: (str, Any) -> Any
    """Returns the currently stored item with the user_key.

    Returns None or the given default value in case there
    is currently no such item stored."""
    return _cached_item_states.get_item_state(user_key, default)


def get_all_item_states():
    # type: () -> ItemStates
    """Returns all stored items of the host that is currently being checked."""
    return _cached_item_states.get_all_item_states()


def clear_item_state(user_key):
    # type: (str) -> None
    """Deletes a stored matching the given key. This needs to be
    the same key as used with set_item_state().

    In case the given item does not exist, the function returns
    without modification."""
    _cached_item_states.clear_item_state(user_key)


def clear_item_states_by_full_keys(full_keys):
    # type: (List[ItemStateKey]) -> None
    """Clears all stored items specified in full_keys.

    The items are deleted by their full identifiers, not only the
    names specified with set_item_state(). For checks this is
    normally (<check_plugin_name>, <item>, <user_key>).
    """
    _cached_item_states.clear_item_states_by_full_keys(full_keys)


def cleanup_item_states():
    # type: () -> None
    """Clears all stored items of the host that is currently being checked."""
    _cached_item_states.clear_all_item_states()


def set_item_state_prefix(*args):
    # type: (ItemStateKeyElement) -> None
    _cached_item_states.set_item_state_prefix(args)


def get_item_state_prefix():
    # type: () -> ItemStateKey
    return _cached_item_states.get_item_state_prefix()


def _unique_item_state_key(user_key):
    # type: (str) -> None
    _cached_item_states.get_unique_item_state_key(user_key)


def continue_on_counter_wrap():
    # type: () -> None
    global g_suppress_on_wrap
    g_suppress_on_wrap = False


# Idea (2): Check_MK should fetch a time stamp for each info. This should also be
# available as a global variable, so that this_time would be an optional argument.
def get_rate(user_key, this_time, this_val, allow_negative=False, onwrap=SKIP, is_rate=False):
    # type: (str, float, float, bool, OnWrap, bool) -> float
    try:
        return _get_counter(user_key, this_time, this_val, allow_negative, is_rate)[1]
    except MKCounterWrapped as e:
        if onwrap is RAISE:
            raise
        elif onwrap is SKIP:
            global g_last_counter_wrap
            g_last_counter_wrap = e
            return 0.0
        else:
            return onwrap


# Helper for get_rate(). Note: this function has been part of the official check API
# for a long time. So we cannot change its call syntax or remove it for the while.
def _get_counter(countername, this_time, this_val, allow_negative=False, is_rate=False):
    # type: (str, float, float, bool, bool) -> Tuple[float, float]
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


def reset_wrapped_counters():
    # type: () -> None
    global g_last_counter_wrap
    g_last_counter_wrap = None


# TODO: Can we remove this? (check API)
def last_counter_wrap():
    # type: () -> Optional[MKCounterWrapped]
    return g_last_counter_wrap


def raise_counter_wrap():
    # type: () -> None
    if g_last_counter_wrap:
        raise g_last_counter_wrap  # pylint: disable=raising-bad-type


def get_average(itemname, this_time, this_val, backlog_minutes, initialize_zero=True):
    # type: (str, float, float, float, bool) -> float
    """Compute average by gliding exponential algorithm

    itemname        : unique ID for storing this average until the next check
    this_time       : timestamp of new value
    backlog         : averaging horizon in minutes
    initialize_zero : assume average of 0.0 when now previous average is stored
    """
    old_state = get_item_state(itemname, None)

    # first call: take current value as average or assume 0.0
    if old_state is None:
        if initialize_zero:
            this_val = 0
        set_item_state(itemname, (this_time, this_val))
        return this_val  # avoid time diff of 0.0 -> avoid division by zero

    # Get previous value and time difference
    last_time, last_val = old_state
    timedif = this_time - last_time

    # Gracefully handle time-anomaly of target systems. We lose
    # one value, but what then heck..
    if timedif < 0:
        timedif = 0

    # Overflow error occurs if weight exceeds 1e308 or falls below 1e-308
    # Under the conditions 0<=percentile<=1, backlog_minutes>=1 and timedif>=0
    # first case is not possible because weight is max. 1.
    # In the second case weight goes to zero.
    try:
        # Compute the weight: We do it like this: First we assume that
        # we get one sample per minute. And that backlog_minutes is the number
        # of minutes we should average over. Then we want that the weight
        # of the values of the last average minutes have a fraction of W%
        # in the result and the rest until infinity the rest (1-W%).
        # Then the weight can be computed as backlog_minutes'th root of 1-W
        percentile = 0.50

        weight_per_minute = (1 - percentile)**(1.0 / backlog_minutes)

        # now let's compute the weight per second. This is done
        weight = weight_per_minute**(timedif / 60.0)

    except OverflowError:
        weight = 0

    new_val = last_val * weight + this_val * (1 - weight)

    set_item_state(itemname, (this_time, new_val))
    return new_val


cmk.base.cleanup.register_cleanup(cleanup_item_states)
