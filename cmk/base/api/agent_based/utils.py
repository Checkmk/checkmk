#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper functions for check devolpment

These are meant to be exposed in the API
"""
from typing import Any, List, MutableMapping, TypeVar
import re
import itertools
from cmk.base.snmp_utils import SNMPTable
from cmk.base.api.agent_based.section_types import AgentSectionContent, SNMPDetectSpec
from cmk.base.api.agent_based.checking_types import IgnoreResultsError

RawSection = TypeVar('RawSection', List[SNMPTable], AgentSectionContent)


def parse_string_table(string_table):
    # type: (RawSection) -> RawSection
    """Identity function

    Provided for developers who don't want to implement a parse function (which they should).
    """
    return string_table


#     ____       _            _
#    |  _ \  ___| |_ ___  ___| |_   ___ _ __   ___  ___
#    | | | |/ _ \ __/ _ \/ __| __| / __| '_ \ / _ \/ __|
#    | |_| |  __/ ||  __/ (__| |_  \__ \ |_) |  __/ (__
#    |____/ \___|\__\___|\___|\__| |___/ .__/ \___|\___|
#                                      |_|


def all_of(spec_0, spec_1, *specs):
    # type: (SNMPDetectSpec, SNMPDetectSpec, SNMPDetectSpec) -> SNMPDetectSpec
    reduced = [l0 + l1 for l0, l1 in itertools.product(spec_0, spec_1)]
    if not specs:
        return reduced
    return all_of(reduced, *specs)


def any_of(*specs):
    # type: (SNMPDetectSpec) -> SNMPDetectSpec
    return sum(specs, [])


def _negate(spec):
    # type: (SNMPDetectSpec) -> SNMPDetectSpec
    assert len(spec) == 1
    assert len(spec[0]) == 1
    return [[(spec[0][0][0], spec[0][0][1], not spec[0][0][2])]]


def matches(oidstr, value):
    # type: (str, str) -> SNMPDetectSpec
    return [[(oidstr, value, True)]]


def contains(oidstr, value):
    # type: (str, str) -> SNMPDetectSpec
    return [[(oidstr, '.*%s.*' % re.escape(value), True)]]


def startswith(oidstr, value):
    # type: (str, str) -> SNMPDetectSpec
    return [[(oidstr, '%s.*' % re.escape(value), True)]]


def endswith(oidstr, value):
    # type: (str, str) -> SNMPDetectSpec
    return [[(oidstr, '.*%s' % re.escape(value), True)]]


def equals(oidstr, value):
    # type: (str, str) -> SNMPDetectSpec
    return [[(oidstr, '%s' % re.escape(value), True)]]


def exists(oidstr):
    # type: (str) -> SNMPDetectSpec
    return [[(oidstr, '.*', True)]]


def not_matches(oidstr, value):
    # type: (str, str) -> SNMPDetectSpec
    return _negate(matches(oidstr, value))


def not_contains(oidstr, value):
    # type: (str, str) -> SNMPDetectSpec
    return _negate(contains(oidstr, value))


def not_startswith(oidstr, value):
    # type: (str, str) -> SNMPDetectSpec
    return _negate(startswith(oidstr, value))


def not_endswith(oidstr, value):
    # type: (str, str) -> SNMPDetectSpec
    return _negate(endswith(oidstr, value))


def not_equals(oidstr, value):
    # type: (str, str) -> SNMPDetectSpec
    return _negate(equals(oidstr, value))


def not_exists(oidstr):
    # type: (str) -> SNMPDetectSpec
    return _negate(exists(oidstr))


#    __     __    _            ____  _                   _   _ _   _ _
#    \ \   / /_ _| |_   _  ___/ ___|| |_ ___  _ __ ___  | | | | |_(_) |___
#     \ \ / / _` | | | | |/ _ \___ \| __/ _ \| '__/ _ \ | | | | __| | / __|
#      \ V / (_| | | |_| |  __/___) | || (_) | | |  __/ | |_| | |_| | \__ \
#       \_/ \__,_|_|\__,_|\___|____/ \__\___/|_|  \___|  \___/ \__|_|_|___/
#


class GetRateError(IgnoreResultsError):
    pass


def get_rate(value_store, key, time, value, raise_overflow=False):
    # type: (MutableMapping[str, Any], str, float, float, bool) -> float
    # TODO (mo): unhack this CMK-3983
    # raise overflow is kwarg only
    last_state = value_store.get(key)
    value_store[key] = (time, value)

    if not last_state or len(last_state) != 2:
        raise GetRateError('Initialized: %r' % key)
    last_time, last_value = last_state

    if time <= last_time:
        raise GetRateError('No time difference')

    rate = float(value - last_value) / (time - last_time)
    if raise_overflow and rate < 0:
        # Do not try to handle wrapper counters. We do not know
        # wether they are 32 or 64 bit. It also could happen counter
        # reset (reboot, etc.). Better is to leave this value undefined
        # and wait for the next check interval.
        raise GetRateError('Value overflow')

    return rate


def get_average(value_store, key, time, value, backlog_minutes):
    # type: (MutableMapping[str, Any], str, float, float, float) -> float
    """Return new average based on current value and last average

    :param value_store:     The Mapping that holds the last value. Usually this will
                            be the value store provided by the API.
    :param key:             Unique ID for storing this average until the next check
    :param time:            Timestamp of new value
    :param value:           The new value
    :param backlog_minutes: Averaging horizon in minutes

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

    """
    stored_value = value_store.get(key, ())
    if len(stored_value) != 3:
        value_store[key] = (time, time, value)
        return value
    start_time, last_time, last_average = stored_value

    # at the current rate, how many values are in the backlog?
    time_diff = time - last_time
    if time_diff <= 0:
        # Gracefully handle time-anomaly of target systems
        return last_average
    backlog_count = (backlog_minutes * 60.) / time_diff

    # go back to regular EMA once the timeseries is twice ↓ the backlog.
    backlog_weight = 0.5**min(1, (time - start_time) / (2 * backlog_minutes * 60.))

    weight = (1 - backlog_weight)**(1.0 / backlog_count)

    average = (1.0 - weight) * value + weight * last_average
    value_store[key] = (start_time, time, average)
    return average
