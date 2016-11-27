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

While a host is being checked this memory is kept in g_item_state.
That is a dictionary. The keys are unique to one check type and
item. The value is free form.

Note: The item state is kept in tmpfs and not reboot-persistant.
Do not store long-time things here. Also do not store complex
structures like log files or stuff.
"""

import os

import cmk.paths
from cmk.exceptions import MKGeneralException

# Constants for counters
SKIP  = None
RAISE = False
ZERO  = 0.0

g_item_state        = {}   # storing counters of one host
g_last_counter_wrap = None #
g_item_state_prefix = []
g_suppress_on_wrap  = True # Suppress check on wrap (raise an exception)
                           # e.g. do not suppress this check on check_mk -nv


class MKCounterWrapped(Exception):
    def __init__(self, reason):
        self.reason = reason
        super(MKCounterWrapped, self).__init__(reason)
    def __str__(self):
        return self.reason


def load(hostname):
    global g_item_state
    filename = cmk.paths.counters_dir + "/" + hostname
    try:
        g_item_state = eval(file(filename).read())
    except:
        g_item_state = {}


def save(hostname):
    filename = cmk.paths.counters_dir + "/" + hostname
    try:
        if not os.path.exists(cmk.paths.counters_dir):
            os.makedirs(cmk.paths.counters_dir)
        file(filename, "w").write("%r\n" % g_item_state)
    except Exception, e:
        raise MKGeneralException("Cannot write to %s: %s" % (filename, traceback.format_exc()))


def set_item_state(user_key, state):
    """Store arbitrary values until the next execution of a check"""
    g_item_state[_unique_item_state_key(user_key)] = state


def get_item_state(user_key, default=None):
    return g_item_state.get(_unique_item_state_key(user_key), default)


def get_all_item_states():
    return g_item_state


def clear_item_state(user_key):
    key = _unique_item_state_key(user_key)
    if key in g_item_state:
        del g_item_state[key]


def clear_item_states_by_full_keys(full_keys):
    for key in full_keys:
        try:
            del g_item_state[key]
        except KeyError:
            pass


def set_item_state_prefix(*args):
    global g_item_state_prefix
    g_item_state_prefix = args


def _unique_item_state_key(user_key):
    return g_item_state_prefix + (user_key,)


def continue_on_counter_wrap():
    global g_suppress_on_wrap
    g_suppress_on_wrap = False


# Idea (2): Check_MK should fetch a time stamp for each info. This should also be
# available as a global variable, so that this_time would be an optional argument.
def get_rate(user_key, this_time, this_val, allow_negative=False, onwrap=SKIP, is_rate=False):
    try:
        return _get_counter(user_key, this_time, this_val, allow_negative, is_rate)[1]
    except MKCounterWrapped, e:
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
    if timedif <= 0: # do not update counter
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
    global g_last_counter_wrap
    g_last_counter_wrap = None


# TODO: Can we remove this? (check API)
def last_counter_wrap():
    return g_last_counter_wrap


def raise_counter_wrap():
    if g_last_counter_wrap:
        raise g_last_counter_wrap # pylint: disable=raising-bad-type


# Compute average by gliding exponential algorithm
# itemname        : unique ID for storing this average until the next check
# this_time       : timestamp of new value
# backlog         : averaging horizon in minutes
# initialize_zero : assume average of 0.0 when now previous average is stored
def get_average(itemname, this_time, this_val, backlog_minutes, initialize_zero = True):
    old_state = get_item_state(itemname, None)

    # first call: take current value as average or assume 0.0
    if old_state is None:
        if initialize_zero:
            this_val = 0
        set_item_state(itemname, (this_time, this_val))
        return this_val # avoid time diff of 0.0 -> avoid division by zero

    # Get previous value and time difference
    last_time, last_val = old_state
    timedif = this_time - last_time

    # Gracefully handle time-anomaly of target systems. We lose
    # one value, but what then heck..
    if timedif < 0:
        timedif = 0

    # Overflow error occurs if weigth exceeds 1e308 or falls below 1e-308
    # Under the conditions 0<=percentile<=1, backlog_minutes>=1 and timedif>=0
    # first case is not possible because weigth is max. 1.
    # In the second case weigth goes to zero.
    try:
        # Compute the weight: We do it like this: First we assume that
        # we get one sample per minute. And that backlog_minutes is the number
        # of minutes we should average over. Then we want that the weight
        # of the values of the last average minutes have a fraction of W%
        # in the result and the rest until infinity the rest (1-W%).
        # Then the weight can be computed as backlog_minutes'th root of 1-W
        percentile = 0.50

        weight_per_minute = (1 - percentile) ** (1.0 / backlog_minutes)

        # now let's compute the weight per second. This is done
        weight = weight_per_minute ** (timedif / 60.0)

    except OverflowError:
        weight = 0

    new_val = last_val * weight + this_val * (1 - weight)

    set_item_state(itemname, (this_time, new_val))
    return new_val
