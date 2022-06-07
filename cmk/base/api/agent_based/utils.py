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
from typing import Any, Callable, Dict, Generator, MutableMapping, Optional, overload, Tuple, Union

import cmk.utils.debug
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import HostName

import cmk.base.plugin_contexts as plugin_contexts  # pylint: disable=cmk-module-layer-violation
import cmk.base.prediction  # pylint: disable=cmk-module-layer-violation
from cmk.base.api.agent_based.checking_classes import IgnoreResultsError, Metric, Result, State
from cmk.base.api.agent_based.section_classes import SNMPDetectSpecification

#     ____       _            _
#    |  _ \  ___| |_ ___  ___| |_   ___ _ __   ___  ___
#    | | | |/ _ \ __/ _ \/ __| __| / __| '_ \ / _ \/ __|
#    | |_| |  __/ ||  __/ (__| |_  \__ \ |_) |  __/ (__
#    |____/ \___|\__\___|\___|\__| |___/ .__/ \___|\___|
#                                      |_|


def all_of(
    spec_0: SNMPDetectSpecification,
    spec_1: SNMPDetectSpecification,
    *specs: SNMPDetectSpecification,
) -> SNMPDetectSpecification:
    """Detect the device if all passed specifications are met

    Args:
        spec_0: A valid specification for SNMP device detection
        spec_1: A valid specification for SNMP device detection

    Returns:
        A valid specification for SNMP device detection

    Example:

        >>> DETECT = all_of(exists("1.2.3.4"), contains("1.2.3.5", "foo"))

    """
    reduced = SNMPDetectSpecification(l0 + l1 for l0, l1 in itertools.product(spec_0, spec_1))
    if not specs:
        return reduced
    return all_of(reduced, *specs)


def any_of(*specs: SNMPDetectSpecification) -> SNMPDetectSpecification:
    """Detect the device if any of the passed specifications are met

    Args:
        spec: A valid specification for SNMP device detection

    Returns:
        A valid specification for SNMP device detection

    Example:

        >>> DETECT = any_of(exists("1.2.3.4"), exists("1.2.3.5"))

    """
    return SNMPDetectSpecification(sum(specs, []))


def _negate(spec: SNMPDetectSpecification) -> SNMPDetectSpecification:
    assert len(spec) == 1
    assert len(spec[0]) == 1
    return SNMPDetectSpecification([[(spec[0][0][0], spec[0][0][1], not spec[0][0][2])]])


def matches(oidstr: str, value: str) -> SNMPDetectSpecification:
    """Detect the device if the value of the OID matches the expression

    Args:
        oidstr: The OID to match the value against
        value: The regular expression that the value of the OID should match

    Returns:
        A valid specification for SNMP device detection

    Example:

        >>> DETECT = matches("1.2.3.4", ".* Server")

    """
    return SNMPDetectSpecification([[(oidstr, value, True)]])


def contains(oidstr: str, value: str) -> SNMPDetectSpecification:
    """Detect the device if the value of the OID contains the given string

    Args:
        oidstr: The OID to match the value against
        value: The substring expected to be in the OIDs value

    Returns:
        A valid specification for SNMP device detection

    Example:

        >>> DETECT = contains("1.2.3", "isco")

    """
    return SNMPDetectSpecification([[(oidstr, ".*%s.*" % re.escape(value), True)]])


def startswith(oidstr: str, value: str) -> SNMPDetectSpecification:
    """Detect the device if the value of the OID starts with the given string

    Args:
        oidstr: The OID to match the value against
        value: The expected start of the OIDs value

    Returns:
        A valid specification for SNMP device detection

    Example:

        >>> DETECT = startswith("1.2.3", "Sol")

    """
    return SNMPDetectSpecification([[(oidstr, "%s.*" % re.escape(value), True)]])


def endswith(oidstr: str, value: str) -> SNMPDetectSpecification:
    """Detect the device if the value of the OID ends with the given string

    Args:
        oidstr: The OID to match the value against
        value: The expected end of the OIDs value

    Returns:
        A valid specification for SNMP device detection

    Example:

        >>> DETECT = endswith("1.2.3", "nix")

    """
    return SNMPDetectSpecification([[(oidstr, ".*%s" % re.escape(value), True)]])


def equals(oidstr: str, value: str) -> SNMPDetectSpecification:
    """Detect the device if the value of the OID equals the given string

    Args:
        oidstr: The OID to match the value against
        value: The expected value of the OID

    Returns:
        A valid specification for SNMP device detection

    Example:

        >>> DETECT = equals("1.2.3", "MySwitch")

    """
    return SNMPDetectSpecification([[(oidstr, "%s" % re.escape(value), True)]])


def exists(oidstr: str) -> SNMPDetectSpecification:
    """Detect the device if the OID exists at all

    Args:
        oidstr: The OID that is required to exist

    Returns:
        A valid specification for SNMP device detection

    Example:

        >>> DETECT = exists("1.2.3")

    """
    return SNMPDetectSpecification([[(oidstr, ".*", True)]])


def not_matches(oidstr: str, value: str) -> SNMPDetectSpecification:
    """The negation of :func:`matches`"""
    return _negate(matches(oidstr, value))


def not_contains(oidstr: str, value: str) -> SNMPDetectSpecification:
    """The negation of :func:`contains`"""
    return _negate(contains(oidstr, value))


def not_startswith(oidstr: str, value: str) -> SNMPDetectSpecification:
    """The negation of :func:`startswith`"""
    return _negate(startswith(oidstr, value))


def not_endswith(oidstr: str, value: str) -> SNMPDetectSpecification:
    """The negation of :func:`endswith`"""
    return _negate(endswith(oidstr, value))


def not_equals(oidstr: str, value: str) -> SNMPDetectSpecification:
    """The negation of :func:`equals`"""
    return _negate(equals(oidstr, value))


def not_exists(oidstr: str) -> SNMPDetectSpecification:
    """The negation of :func:`exists`"""
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
) -> Tuple[State, str]:
    # Typing says that levels are either None, or a Tuple of float.
    # However we also deal with (None, None) to avoid crashes of custom plugins.
    # CRIT ?
    if levels_upper and levels_upper[1] is not None and value >= levels_upper[1]:
        return State.CRIT, _levelsinfo_ty("at", levels_upper, render_func)
    if levels_lower and levels_lower[1] is not None and value < levels_lower[1]:
        return State.CRIT, _levelsinfo_ty("below", levels_lower, render_func)

    # WARN ?
    if levels_upper and levels_upper[0] is not None and value >= levels_upper[0]:
        return State.WARN, _levelsinfo_ty("at", levels_upper, render_func)
    if levels_lower and levels_lower[0] is not None and value < levels_lower[0]:
        return State.WARN, _levelsinfo_ty("below", levels_lower, render_func)

    return State.OK, ""


def _levelsinfo_ty(
    preposition: str, levels: Tuple[float, float], render_func: Callable[[float], str]
) -> str:
    # Again we are forgiving if we get passed 'None' in the levels.
    warn_str = "never" if levels[0] is None else render_func(levels[0])
    crit_str = "never" if levels[1] is None else render_func(levels[1])
    return " (warn/crit %s %s/%s)" % (preposition, warn_str, crit_str)


@overload
def check_levels(
    value: float,
    *,
    levels_upper: Optional[Tuple[float, float]] = None,
    levels_lower: Optional[Tuple[float, float]] = None,
    metric_name: None = None,
    render_func: Optional[Callable[[float], str]] = None,
    label: Optional[str] = None,
    boundaries: Optional[Tuple[Optional[float], Optional[float]]] = None,
    notice_only: bool = False,
) -> Generator[Result, None, None]:
    pass


@overload
def check_levels(
    value: float,
    *,
    levels_upper: Optional[Tuple[float, float]] = None,
    levels_lower: Optional[Tuple[float, float]] = None,
    metric_name: str = "",
    render_func: Optional[Callable[[float], str]] = None,
    label: Optional[str] = None,
    boundaries: Optional[Tuple[Optional[float], Optional[float]]] = None,
    notice_only: bool = False,
) -> Generator[Union[Result, Metric], None, None]:
    pass


def check_levels(
    value: float,
    *,
    levels_upper: Optional[Tuple[float, float]] = None,
    levels_lower: Optional[Tuple[float, float]] = None,
    metric_name: Optional[str] = None,
    render_func: Optional[Callable[[float], str]] = None,
    label: Optional[str] = None,
    boundaries: Optional[Tuple[Optional[float], Optional[float]]] = None,
    notice_only: bool = False,
) -> Generator[Union[Result, Metric], None, None]:
    """Generic function for checking a value against levels.

    Args:

        value:        The currently measured value
        levels_upper: A pair of upper thresholds, ie. warn and crit. If value is larger than these,
                      the service goes to **WARN** or **CRIT**, respecively.
        levels_lower: A pair of lower thresholds, ie. warn and crit. If value is smaller than these,
                      the service goes to **WARN** or **CRIT**, respecively.
        metric_name:  The name of the datasource in the RRD that corresponds to this value
                      or None in order not to generate a metric.
        render_func:  A single argument function to convert the value from float into a
                      human readable string.
        label:        The label to prepend to the output.
        boundaries:   Minimum and maximum to add to the metric.
        notice_only:  Only show up in service output if not OK (otherwise in details).
                      See `notice` keyword of `Result` class.

    Example:

        >>> result, metric = check_levels(
        ...     23.0,
        ...     levels_upper=(12., 42.),
        ...     metric_name="temperature",
        ...     label="Fridge",
        ...     render_func=lambda v: "%.1f°" % v,
        ... )
        >>> print(result.summary)
        Fridge: 23.0° (warn/crit at 12.0°/42.0°)
        >>> print(metric)
        Metric('temperature', 23.0, levels=(12.0, 42.0))

    """

    def default_render_function(f: float) -> str:
        return "%.2f" % f

    if render_func is None:
        render_func = default_render_function

    info_text = str(render_func(value))  # forgive wrong output type
    if label:
        info_text = "%s: %s" % (label, info_text)

    value_state, levels_text = _do_check_levels(value, levels_upper, levels_lower, render_func)

    if notice_only:
        yield Result(state=value_state, notice=info_text + levels_text)
    else:
        yield Result(state=value_state, summary=info_text + levels_text)
    if metric_name:
        yield Metric(metric_name, value, levels=levels_upper, boundaries=boundaries)


def check_levels_predictive(
    value: float,
    *,
    levels: Dict[str, Any],
    metric_name: str,
    render_func: Optional[Callable[[float], str]] = None,
    label: Optional[str] = None,
    boundaries: Optional[Tuple[Optional[float], Optional[float]]] = None,
) -> Generator[Union[Result, Metric], None, None]:
    """Generic function for checking a value against levels.

    Args:

        value:        Currently measured value
        levels:       Predictive levels. These are used automatically.
                      Lower levels are imposed if the passed dictionary contains "lower"
                      as key, upper levels are imposed if it contains "upper" or
                      "levels_upper_min" as key.
                      If value is lower/higher than these, the service goes to **WARN**
                      or **CRIT**, respecively.
        metric_name:  Name of the datasource in the RRD that corresponds to this value
        render_func:  Single argument function to convert the value from float into a
                      human readable string.
                      readable fashion
        label:        Label to prepend to the output.
        boundaries:   Minimum and maximum to add to the metric.

    """
    if render_func is None:
        render_func = "{:.2f}".format

    # validate the metric name, before we can get the levels.
    _ = Metric(metric_name, value)

    try:
        ref_value, levels_tuple = cmk.base.prediction.get_levels(
            HostName(plugin_contexts.host_name()),
            plugin_contexts.service_description(),
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
        yield Result(state=State.UNKNOWN, summary="%s" % e)
        return

    levels_upper = (
        None
        if levels_tuple[0] is None or levels_tuple[1] is None
        else (levels_tuple[0], levels_tuple[1])
    )

    levels_lower = (
        None
        if levels_tuple[2] is None or levels_tuple[3] is None
        else (levels_tuple[2], levels_tuple[3])
    )

    value_state, levels_text = _do_check_levels(value, levels_upper, levels_lower, render_func)

    if label:
        info_text = "%s: %s%s" % (label, render_func(value), predictive_levels_msg)
    else:
        info_text = "%s%s" % (render_func(value), predictive_levels_msg)

    yield Result(state=value_state, summary=info_text + levels_text)
    yield Metric(metric_name, value, levels=levels_upper, boundaries=boundaries)
    if ref_value:
        yield Metric("predict_%s" % metric_name, ref_value)


#    __     __    _            ____  _                   _   _ _   _ _
#    \ \   / /_ _| |_   _  ___/ ___|| |_ ___  _ __ ___  | | | | |_(_) |___
#     \ \ / / _` | | | | |/ _ \___ \| __/ _ \| '__/ _ \ | | | | __| | / __|
#      \ V / (_| | | |_| |  __/___) | || (_) | | |  __/ | |_| | |_| | \__ \
#       \_/ \__,_|_|\__,_|\___|____/ \__\___/|_|  \___|  \___/ \__|_|_|___/
#


class GetRateError(IgnoreResultsError):
    """The exception raised by :func:`.get_rate`.
    If unhandled, this exception will make the service go stale.
    """


def get_rate(
    value_store: MutableMapping[str, Any],
    key: str,
    time: float,
    value: float,
    *,
    raise_overflow: bool = False,
) -> float:
    """Return a rate based on current value and time and last value and time

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
    last_state = value_store.get(key)
    value_store[key] = (time, value)

    if not last_state or len(last_state) != 2:
        raise GetRateError("Initialized: %r" % key)
    last_time, last_value = last_state

    if time <= last_time:
        raise GetRateError("No time difference")

    rate = float(value - last_value) / (time - last_time)
    if raise_overflow and rate < 0:
        # Do not try to handle wrapper counters. We do not know
        # wether they are 32 or 64 bit. It also could happen counter
        # reset (reboot, etc.). Better is to leave this value undefined
        # and wait for the next check interval.
        raise GetRateError("Value overflow")

    return rate


def get_average(
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
    backlog_count = (backlog_minutes * 60.0) / time_diff

    # go back to regular EMA once the timeseries is twice ↓ the backlog.
    backlog_weight = 0.5 ** min(1, (time - start_time) / (2 * backlog_minutes * 60.0))

    weight = (1 - backlog_weight) ** (1.0 / backlog_count)

    average = (1.0 - weight) * value + weight * last_average
    value_store[key] = (start_time, time, average)
    return average
