#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Any, Generator, MutableMapping, Optional, Tuple, TypedDict, Union

from ..agent_based_api.v1 import check_levels, get_average, get_rate, Result
from ..agent_based_api.v1 import State as state
from ..agent_based_api.v1.render import timespan
from ..agent_based_api.v1.type_defs import CheckResult

StatusType = int
TempUnitType = str
LevelModes = str

TwoLevelsType = Tuple[Optional[float], Optional[float]]
FourLevelsType = Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]
LevelsType = Union[TwoLevelsType, FourLevelsType]
TrendComputeDict = TypedDict(
    "TrendComputeDict",
    {
        "period": int,
        "trend_levels": TwoLevelsType,
        "trend_levels_lower": TwoLevelsType,
        "trend_timeleft": TwoLevelsType,
    },
    total=False,
)
TempParamDict = TypedDict(
    "TempParamDict",
    {
        "input_unit": TempUnitType,
        "output_unit": TempUnitType,
        "levels": TwoLevelsType,
        "levels_lower": TwoLevelsType,
        "device_levels_handling": LevelModes,
        "trend_compute": TrendComputeDict,
    },
    total=False,
)
TempParamType = Union[None, TwoLevelsType, FourLevelsType, TempParamDict]


def fahrenheit_to_celsius(tempf, relative=False):
    if tempf is None:
        return None

    if relative:
        return float(tempf) * (5.0 / 9.0)
    return (float(tempf) - 32) * (5.0 / 9.0)


def celsius_to_fahrenheit(tempc, relative=False):
    if tempc is None:
        return None

    if relative:
        return float(tempc) * (9.0 / 5.0)
    return (float(tempc) * (9.0 / 5.0)) + 32


def to_celsius(reading, unit, relative=False):
    if isinstance(reading, tuple):
        return tuple(to_celsius(x, unit, relative) for x in reading)
    if unit == "f":
        return fahrenheit_to_celsius(reading, relative)
    if unit == "k":
        if relative:
            return reading
        if reading is None:
            return None
        return reading - 273.15
    return reading


def from_celsius(tempc, unit, relative=False):
    if unit == "f":
        return celsius_to_fahrenheit(tempc, relative)
    if unit == "k":
        if relative:
            return tempc
        return tempc + 273.15
    return tempc


# Format number according to its datatype
def render_temp(n: float, output_unit: str, relative: bool = False, *, sign: bool = False) -> str:
    """
    >>> render_temp(12., "c", False, sign=False)
    '12.0'
    >>> render_temp(12, "c", False, sign=True)
    '+12'
    >>> render_temp(-12., "f", False, sign=False)
    '10.4'

    """
    value = from_celsius(n, output_unit, relative)
    template = "%%%s%s" % ("+" if sign else "", "d" if isinstance(n, int) else ".1f")
    return template % value


def _render_temp_with_unit(temp: float, unit: str) -> str:
    return render_temp(temp, unit) + temp_unitsym[unit]


temp_unitsym = {
    "c": "°C",
    "f": "°F",
    "k": "K",
}


def _migrate_params(params: TempParamType) -> TempParamDict:
    """Migrate legacy params values to the current one.

    Args:
        params: Anything which was once a valid params entry. Concretely, 2-tuples, 4-tuples and
                dicts with the correct values are allowed. In the case of a dict, nothing is done.

    Returns:
        A dict.

    Examples:

        >>> _migrate_params((1, 2))
        {'levels': (1, 2)}

        >>> _migrate_params((1, 2, 3, 4))
        {'levels': (1, 2), 'levels_lower': (3, 4)}

        >>> _migrate_params({})
        {}

        >>> _migrate_params(None)
        {}

    """
    # Convert legacy tuple params into new dict
    if isinstance(params, tuple):
        if len(params) == 4:
            # mypy doesn't handle this tuple slicing very well.
            params = {
                "levels": params[:2],
                "levels_lower": params[2:],  # type: ignore[typeddict-item]
            }
        else:
            params = {"levels": params[:2]}
    elif params is None:
        params = {}
    return params


def _validate_levels(
    levels: Optional[Tuple[Optional[float], Optional[float]]] = None,
) -> Optional[Tuple[float, float]]:
    if levels is None:
        return None

    warn, crit = levels
    if warn is None or crit is None:
        return None

    return warn, crit


def _check_trend(
    value_store: MutableMapping[str, Any],
    temp: float,
    params: TrendComputeDict,
    output_unit: str,
    crit_temp: Optional[float],
    crit_temp_lower: Optional[float],
    unique_name: str,
) -> Generator[Result, None, None]:
    trend_range_min = params["period"]
    this_time = time.time()

    # current rate since last check
    rate = get_rate(
        value_store=value_store,
        key="temp.%s.delta" % unique_name,
        time=this_time,
        value=temp,
    )

    # average trend, initialized with initial temperature value on first check
    rate_avg = get_average(
        value_store=value_store,
        key="temp.%s.trend" % unique_name,
        time=this_time,
        value=rate,
        backlog_minutes=trend_range_min,
    )

    trend = rate_avg * trend_range_min * 60.0
    levels_upper_trend = _validate_levels(params.get("trend_levels"))

    levels_lower_trend = _validate_levels(params.get("trend_levels_lower"))
    if levels_lower_trend is not None:
        # GUI representation of this parameter is labelled 'temperature decrease'; the user may input this
        # as a positive or negative value
        levels_lower_trend = (abs(levels_lower_trend[0]) * -1, abs(levels_lower_trend[1]) * -1)

    yield from check_levels(
        value=trend,
        levels_upper=levels_upper_trend,
        levels_lower=levels_lower_trend,
        label="Temperature trend",
        render_func=lambda trend: render_temp(
            trend,
            output_unit,
            relative=True,
            sign=True,
        )
        + temp_unitsym[output_unit]
        + " per "
        + str(trend_range_min)
        + " min",
    )

    if "trend_timeleft" not in params:
        return

    limit = crit_temp if trend > 0 else crit_temp_lower
    if limit is None:
        # crit levels may not be set
        return

    # compute time until temperature limit is reached
    warn_timeleft_min, crit_timeleft_min = params["trend_timeleft"]
    if warn_timeleft_min is None or crit_timeleft_min is None:
        levels_timeleft_sec = None
    else:
        levels_timeleft_sec = (warn_timeleft_min * 60.0, crit_timeleft_min * 60.0)

    diff_to_limit = limit - temp
    seconds_left = float(diff_to_limit / rate_avg)

    yield from check_levels(
        value=seconds_left,
        levels_lower=levels_timeleft_sec,
        render_func=timespan,
        label="Time until temperature limit reached",
    )


def check_temperature(  # pylint: disable=too-many-branches
    reading: float,
    params: TempParamType,
    *,
    unique_name: str,
    value_store: MutableMapping[str, Any],
    dev_unit: Optional[str] = "c",
    dev_levels: Optional[Tuple[float, float]] = None,
    dev_levels_lower: Optional[Tuple[float, float]] = None,
    dev_status: Optional[StatusType] = None,
    dev_status_name: Optional[str] = None,
) -> CheckResult:
    """This function checks the temperature value against specified levels and issues a warn/cirt
    message. Levels can be supplied by the user or the device. The user has the possibility to configure
    the preferred levels. Additionally, it is possible to check temperature trends. All internal
    computations are done in Celsius.

    Args:
        reading (Number): The numeric temperature value itself.
        params (dict): A dictionary giving the user's configuration. See below.
        unique_name (str): The name under which to track performance data for trend computation.
        value_store: The Value Store to used for trend computation
        dev_unit (str): The unit. May be one of 'c', 'f' or 'k'. Default is 'c'.
        dev_levels (Optional[LevelsType]): The upper levels (warn, crit)
        dev_levels_lower (Optional[LevelsType]): The lower levels (warn, crit)
        dev_status (Optional[StatusType]): The status according to the device itself.
        dev_status_name (Optional[str]): The device's own name for the status.

    Configuration:
        The parameter "params" may contain user configurable settings with the following keys:
            - input_unit -- The device's unit, user defined.
            - output_unit -- The unit by which to report.
            - levels -- Upper levels, user defined.
            - levels_lower -- Lower levels, user defined.
            - device_levels_handling -- One of the following modes:
                - usrdefault (default) -- Use user's levels, if not there use device's levels.
                - usr -- Always use user's levels. Ignore device's levels.
                - devdefault -- Use device's levels, if not there use user's levels.
                - dev -- Always use device's levels. Ignore users's levels.
                - best -- Report the least critical status of user's and device's levels.
                - worst -- Report the most critical status of user's and device's levels.
            - trend_compute -- If set calculates temperature trend:
                - period -- The period for the trend computation in minutes, e.g. rise of 12°/60 min
                - trend_levels -- Temperature increase per period. (warn, crit)
                - trend_levels_lower -- Temperature decrease per period. (warn, crit)
                - trend_timeleft -- Time left until a CRITICAL temperature level is reached (upper or lower).

    GUI:
         - cmk/gui/plugins/wato/check_parameters/temperature.py

    """
    # Convert legacy tuple params into new dict
    params = _migrate_params(params)

    input_unit = params.get("input_unit", dev_unit)
    output_unit = params.get("output_unit", "c")
    temp = to_celsius(reading, input_unit)

    # User levels are already in Celsius
    usr_levels_upper = _validate_levels(params.get("levels"))
    usr_levels_lower = _validate_levels(params.get("levels_lower"))
    dev_levels_upper = to_celsius(dev_levels, dev_unit)
    dev_levels_lower = to_celsius(dev_levels_lower, dev_unit)

    device_levels_handling = params.get("device_levels_handling", "usrdefault")

    usr_result, usr_metric = check_levels(
        value=temp,
        metric_name="temp",
        levels_upper=usr_levels_upper,
        levels_lower=usr_levels_lower,
        label="Temperature",
        render_func=lambda temp: _render_temp_with_unit(temp, output_unit),
    )

    assert isinstance(usr_result, Result)

    dev_result, dev_metric = check_levels(
        value=temp,
        metric_name="temp",
        levels_upper=dev_levels_upper,
        levels_lower=dev_levels_lower,
        label="Temperature",
        render_func=lambda temp: _render_temp_with_unit(temp, output_unit),
    )

    assert isinstance(dev_result, Result)

    usr_results = [usr_result]
    dev_results = [dev_result]
    if params.get("trend_compute") is not None:
        usr_results.extend(
            result
            for result in _check_trend(
                value_store=value_store,
                temp=temp,
                params=params["trend_compute"],
                output_unit=output_unit,
                crit_temp=usr_levels_upper[1] if usr_levels_upper is not None else None,
                crit_temp_lower=usr_levels_lower[1] if usr_levels_lower is not None else None,
                unique_name=unique_name,
            )
        )

        dev_results.extend(
            result
            for result in _check_trend(
                value_store=value_store,
                temp=temp,
                params=params["trend_compute"],
                output_unit=output_unit,
                crit_temp=dev_levels_upper[1] if dev_levels_upper is not None else None,
                crit_temp_lower=dev_levels_lower[1] if dev_levels_lower is not None else None,
                unique_name=unique_name + ".dev",
            )
        )

    if dev_status is not None:
        dev_results.append(
            Result(
                state=state(dev_status),
                notice="State on device: %s" % dev_status_name,
            )
        )

    if device_levels_handling == "usr":
        yield usr_metric
        yield from usr_results
        yield Result(state=state.OK, notice="Configuration: only use user levels")
        return

    if device_levels_handling == "dev":
        yield dev_metric
        yield from dev_results
        yield Result(state=state.OK, notice="Configuration: only use device levels")
        return

    if device_levels_handling == "usrdefault":
        if usr_levels_upper is not None or usr_levels_lower is not None:
            yield usr_metric
            yield from usr_results
            suffix = "(used user levels)"

        elif dev_levels_upper is not None or dev_levels_lower is not None:
            yield dev_metric
            yield from dev_results
            suffix = "(used device levels)"

        else:
            yield usr_metric
            yield from usr_results
            suffix = "(no levels found)"

        yield Result(
            state=state.OK,
            notice="Configuration: prefer user levels over device levels %s" % suffix,
        )

        return

    if device_levels_handling == "devdefault":
        if dev_levels_upper is not None or dev_levels_lower is not None:
            yield dev_metric
            yield from dev_results
            suffix = "(used device levels)"

        elif usr_levels_upper is not None or usr_levels_lower is not None:
            yield usr_metric
            yield from usr_results
            suffix = "(used user levels)"

        else:
            yield dev_metric
            yield from dev_results
            suffix = "(no levels found)"

        yield Result(
            state=state.OK,
            notice="Configuration: prefer device levels over user levels %s" % suffix,
        )

        return

    if device_levels_handling == "worst":
        usr_overall_state = state.worst(*(result.state for result in usr_results))
        dev_overall_state = state.worst(*(result.state for result in dev_results))
        worst_state = state.worst(usr_overall_state, dev_overall_state)

        if usr_overall_state == worst_state:
            yield usr_metric
            yield from usr_results
        else:
            yield dev_metric
            yield from dev_results

        yield Result(state=state.OK, notice="Configuration: show most critical state")

        return

    if device_levels_handling == "best":
        usr_overall_state = state.worst(*(result.state for result in usr_results))
        dev_overall_state = state.worst(*(result.state for result in dev_results))
        best_state = state.best(usr_overall_state, dev_overall_state)

        if usr_overall_state == best_state:
            yield usr_metric
            yield from usr_results
        else:
            yield dev_metric
            yield from dev_results

        yield Result(state=state.OK, notice="Configuration: show least critical state")

        return
