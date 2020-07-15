#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper functions for check devolpment

These are meant to be exposed in the API
"""
import itertools
import re
from typing import Any, Callable, Generator, MutableMapping, Optional, Tuple, Union

import cmk.utils.debug
from cmk.utils.exceptions import MKGeneralException

from cmk.snmplib.type_defs import SNMPDetectSpec

import cmk.base.check_api_utils as check_api_utils
import cmk.base.prediction
from cmk.base.api.agent_based.checking_types import IgnoreResultsError, Metric, Result, state


# annotating this breaks validation.
# yet another reason to not use this.
def parse_to_string_table(string_table):
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


def all_of(spec_0: SNMPDetectSpec, spec_1: SNMPDetectSpec,
           *specs: SNMPDetectSpec) -> SNMPDetectSpec:
    reduced = [l0 + l1 for l0, l1 in itertools.product(spec_0, spec_1)]
    if not specs:
        return reduced
    return all_of(reduced, *specs)


def any_of(*specs: SNMPDetectSpec) -> SNMPDetectSpec:
    return sum(specs, [])


def _negate(spec: SNMPDetectSpec) -> SNMPDetectSpec:
    assert len(spec) == 1
    assert len(spec[0]) == 1
    return [[(spec[0][0][0], spec[0][0][1], not spec[0][0][2])]]


def matches(oidstr: str, value: str) -> SNMPDetectSpec:
    return [[(oidstr, value, True)]]


def contains(oidstr: str, value: str) -> SNMPDetectSpec:
    return [[(oidstr, '.*%s.*' % re.escape(value), True)]]


def startswith(oidstr: str, value: str) -> SNMPDetectSpec:
    return [[(oidstr, '%s.*' % re.escape(value), True)]]


def endswith(oidstr: str, value: str) -> SNMPDetectSpec:
    return [[(oidstr, '.*%s' % re.escape(value), True)]]


def equals(oidstr: str, value: str) -> SNMPDetectSpec:
    return [[(oidstr, '%s' % re.escape(value), True)]]


def exists(oidstr: str) -> SNMPDetectSpec:
    return [[(oidstr, '.*', True)]]


def not_matches(oidstr: str, value: str) -> SNMPDetectSpec:
    return _negate(matches(oidstr, value))


def not_contains(oidstr: str, value: str) -> SNMPDetectSpec:
    return _negate(contains(oidstr, value))


def not_startswith(oidstr: str, value: str) -> SNMPDetectSpec:
    return _negate(startswith(oidstr, value))


def not_endswith(oidstr: str, value: str) -> SNMPDetectSpec:
    return _negate(endswith(oidstr, value))


def not_equals(oidstr: str, value: str) -> SNMPDetectSpec:
    return _negate(equals(oidstr, value))


def not_exists(oidstr: str) -> SNMPDetectSpec:
    return _negate(exists(oidstr))


#          _               _        _                _
#      ___| |__   ___  ___| | __   | | _____   _____| |___
#     / __| '_ \ / _ \/ __| |/ /   | |/ _ \ \ / / _ \ / __|
#    | (__| | | |  __/ (__|   <    | |  __/\ V /  __/ \__ \
#     \___|_| |_|\___|\___|_|\_\___|_|\___| \_/ \___|_|___/
#                             |_____|


def _do_check_levels(
    value: float,
    levels_upper: Optional[Tuple[float, float]],
    levels_lower: Optional[Tuple[float, float]],
    render_func: Callable[[float], str],
) -> Tuple[state, str]:
    # Typing says that levels are either None, or a Tuple of float.
    # However we also deal with (None, None) to avoid crashes of custom plugins.
    # CRIT ?
    if levels_upper and levels_upper[1] is not None and value >= levels_upper[1]:
        return state.CRIT, _levelsinfo_ty("at", levels_upper, render_func)
    if levels_lower and levels_lower[1] is not None and value < levels_lower[1]:
        return state.CRIT, _levelsinfo_ty("below", levels_lower, render_func)

    # WARN ?
    if levels_upper and levels_upper[0] is not None and value >= levels_upper[0]:
        return state.WARN, _levelsinfo_ty("at", levels_upper, render_func)
    if levels_lower and levels_lower[0] is not None and value < levels_lower[0]:
        return state.WARN, _levelsinfo_ty("below", levels_lower, render_func)

    return state.OK, ""


def _levelsinfo_ty(preposition: str, levels: Tuple[float, float],
                   render_func: Callable[[float], str]) -> str:
    # Again we are forgiving if we get passed 'None' in the levels.
    warn_str = "never" if levels[0] is None else render_func(levels[0])
    crit_str = "never" if levels[1] is None else render_func(levels[1])
    return " (warn/crit %s %s/%s)" % (preposition, warn_str, crit_str)


def check_levels(
    value: float,
    *,
    levels_upper=None,  # tpye: Optional[Tuple[float, float]]
    levels_lower=None,  # tpye: Optional[Tuple[float, float]]
    metric_name: str = None,
    render_func: Callable[[float], str] = None,
    label: str = None,
    boundaries: Optional[Tuple[Optional[float], Optional[float]]] = None,
) -> Generator[Union[Result, Metric], None, None]:
    """Generic function for checking a value against levels.

    :param value:        Currently measured value
    :param levels_upper: Pair of upper thresholds. If value is larger than these, the
                         service goes to **WARN** or **CRIT**, respecively.
    :param levels_lower: Pair of lower thresholds. If value is smaller than these, the
                         service goes to **WARN** or **CRIT**, respecively.
    :param metric_name:  Name of the datasource in the RRD that corresponds to this value
                         or None in order to skip perfdata
    :param render_func:  Single argument function to convert the value from float into a
                         human readable string.
                         readable fashion
    :param label:        Label to prepend to the output.
    :param boundaries:   Minimum and maximum to add to the metric.
    """
    if render_func is None:
        render_func = lambda f: "%.2f" % f

    info_text = str(render_func(value))  # forgive wrong output type
    if label:
        info_text = "%s: %s" % (label, info_text)

    value_state, levels_text = _do_check_levels(value, levels_upper, levels_lower, render_func)

    yield Result(state=value_state, summary=info_text + levels_text)
    if metric_name:
        yield Metric(metric_name, value, levels=levels_upper, boundaries=boundaries)


def check_levels_predictive(
    value: float,
    *,
    levels,  # tpye: Dict[str, Any]
    metric_name: str,
    render_func: Optional[Callable[[float], str]] = None,
    label: Optional[str] = None,
    boundaries: Optional[Tuple[Optional[float], Optional[float]]] = None,
) -> Generator[Union[Result, Metric], None, None]:
    """Generic function for checking a value against levels.

    :param value:        Currently measured value
    :param levels:       Predictive levels. These are used automatically.
                         Lower levels are imposed if the passed dictionary contains "lower"
                         as key, upper levels are imposed if it contains "upper" or
                         "levels_upper_min" as key.
                         If value is lower/higher than these, the service goes to **WARN**
                         or **CRIT**, respecively.
    :param metric_name:  Name of the datasource in the RRD that corresponds to this value
    :param render_func:  Single argument function to convert the value from float into a
                         human readable string.
                         readable fashion
    :param label:        Label to prepend to the output.
    :param boundaries:   Minimum and maximum to add to the metric.
    """
    if render_func is None:
        render_func = "%.2f".format

    # validate the metric name, before we can get the levels.
    Metric.validate_name(metric_name)

    try:
        ref_value, levels_tuple = cmk.base.prediction.get_levels(
            check_api_utils.host_name(),
            check_api_utils.service_description(),
            metric_name,
            levels,
            "MAX",
        )
        if ref_value:
            predictive_levels_msg = " (predicted reference: %s)" % render_func(ref_value)
        else:
            predictive_levels_msg = " (no reference for prediction yet)"

    except MKGeneralException as e:
        ref_value = None
        levels_tuple = (None, None, None, None)
        predictive_levels_msg = " (no reference for prediction: %s)" % e

    except Exception as e:
        if cmk.utils.debug.enabled():
            raise
        yield Result(state=state.UNKNOWN, summary="%s" % e)
        return

    levels_upper = (None if levels_tuple[0] is None or levels_tuple[1] is None else
                    (levels_tuple[0], levels_tuple[1]))

    levels_lower = (None if levels_tuple[2] is None or levels_tuple[3] is None else
                    (levels_tuple[2], levels_tuple[3]))

    value_state, levels_text = _do_check_levels(value, levels_upper, levels_lower, render_func)

    if label:
        info_text = "%s: %s%s" % (label, render_func(value), predictive_levels_msg)
    else:
        info_text = "%s%s" % (render_func(value), predictive_levels_msg)

    yield Result(state=value_state, summary=info_text + levels_text)
    yield Metric(metric_name, value, levels=levels_upper, boundaries=boundaries)
    if ref_value:
        Metric("predict_%s" % metric_name, ref_value)


#    __     __    _            ____  _                   _   _ _   _ _
#    \ \   / /_ _| |_   _  ___/ ___|| |_ ___  _ __ ___  | | | | |_(_) |___
#     \ \ / / _` | | | | |/ _ \___ \| __/ _ \| '__/ _ \ | | | | __| | / __|
#      \ V / (_| | | |_| |  __/___) | || (_) | | |  __/ | |_| | |_| | \__ \
#       \_/ \__,_|_|\__,_|\___|____/ \__\___/|_|  \___|  \___/ \__|_|_|___/
#


class GetRateError(IgnoreResultsError):
    pass


def get_rate(value_store: MutableMapping[str, Any],
             key: str,
             time: float,
             value: float,
             *,
             raise_overflow: bool = False) -> float:
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


def get_average(value_store: MutableMapping[str, Any], key: str, time: float, value: float,
                backlog_minutes: float) -> float:
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
