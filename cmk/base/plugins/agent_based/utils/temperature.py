#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Union, Tuple, Optional, TypedDict
import time
from cmk.base.api.agent_based.utils import (
    check_levels,
    get_rate,
    get_average,
)
from cmk.base.api.agent_based.render import (
    timespan,)
from ..agent_based_api.v0.type_defs import (
    CheckGenerator,)

# TODO: Just for documentation purposes for now, add typing_extensions and use this.
#
# StatusType = Union[Literal[0], Literal[1], Literal[2], Literal[3]]
# TempUnitType = Union[Literal['c'],  # celsius
#                      Literal['k'],  # kelvin = celsius starting at absolute 0
#                      Literal['f'],  # fahrenheit
#                     ]
# LevelModes = Union[Literal['worst'], Literal['best'], Literal['dev'], Literal['devdefault'],
#                    Literal['usr'], Literal['usrdefault']]

StatusType = int
TempUnitType = str
LevelModes = str

Number = Union[int, float]

# Generic Check Type. Can be used elsewhere too.

TwoLevelsType = Tuple[Optional[Number], Optional[Number]]
FourLevelsType = Tuple[Optional[Number], Optional[Number], Optional[Number], Optional[Number]]
LevelsType = Union[TwoLevelsType, FourLevelsType]
TrendComputeDict = TypedDict(
    'TrendComputeDict',
    {
        'period': int,
        'trend_levels': TwoLevelsType,
        'trend_levels_lower': TwoLevelsType,
        'trend_timeleft': TwoLevelsType,
    },
    total=False,
)
TempParamDict = TypedDict(
    'TempParamDict',
    {
        'input_unit': TempUnitType,
        'output_unit': TempUnitType,
        'levels': TwoLevelsType,
        'levels_lower': TwoLevelsType,
        'device_levels_handling': LevelModes,
        'trend_compute': TrendComputeDict,
    },
    total=False,
)
TempParamType = Union[None, TwoLevelsType, FourLevelsType, TempParamDict]


def minn(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return min(a, b)


def maxx(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return max(a, b)


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
        return tuple([to_celsius(x, unit, relative) for x in reading])
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


temp_unitsym = {
    "c": u"°C",
    "f": u"°F",
    "k": u"K",
}


def check_temperature_determine_levels(dlh, usr_warn, usr_crit, usr_warn_lower, usr_crit_lower,
                                       dev_warn, dev_crit, dev_warn_lower, dev_crit_lower):

    # Default values if none of the branches will match.
    warn = crit = warn_lower = crit_lower = None

    # Ignore device's own levels
    if dlh == "usr":
        warn, crit, warn_lower, crit_lower = usr_warn, usr_crit, usr_warn_lower, usr_crit_lower

    # Only use device's levels, ignore yours
    elif dlh == "dev":
        warn, crit, warn_lower, crit_lower = dev_warn, dev_crit, dev_warn_lower, dev_crit_lower

    # The following four cases are all identical, if either *only* device levels or *only*
    # user levels exist (or no levels at all).

    # Use least critical of your and device's levels. If just one of both is defined,
    # take that. max deals correctly with None here. min does not work because None < int.
    # minn is a min that deals with None in the way we want here.
    elif dlh == "best":
        warn, crit = maxx(usr_warn, dev_warn), maxx(usr_crit, dev_crit)
        warn_lower, crit_lower = minn(usr_warn_lower,
                                      dev_warn_lower), minn(usr_crit_lower, dev_crit_lower)

    # Use most critical of your and device's levels
    elif dlh == "worst":
        warn, crit = minn(usr_warn, dev_warn), minn(usr_crit, dev_crit)
        warn_lower, crit_lower = maxx(usr_warn_lower,
                                      dev_warn_lower), maxx(usr_crit_lower, dev_crit_lower)

    # Use user's levels if present, otherwise the device's
    elif dlh == "usrdefault":
        if usr_warn is not None and usr_crit is not None:
            warn, crit = usr_warn, usr_crit
        else:
            warn, crit = dev_warn, dev_crit
        if usr_warn_lower is not None and usr_crit_lower is not None:
            warn_lower, crit_lower = usr_warn_lower, usr_crit_lower
        else:
            warn_lower, crit_lower = dev_warn_lower, dev_crit_lower

    # Use device's levels if present, otherwise yours
    elif dlh == "devdefault":
        if dev_warn is not None and dev_crit is not None:
            warn, crit = dev_warn, dev_crit
        else:
            warn, crit = usr_warn, usr_crit

        if dev_warn_lower is not None and dev_crit_lower is not None:
            warn_lower, crit_lower = dev_warn_lower, dev_crit_lower
        else:
            warn_lower, crit_lower = usr_warn_lower, usr_crit_lower

    return warn, crit, warn_lower, crit_lower


def _check_trend(
    value_store,
    temp: float,
    params: TrendComputeDict,
    output_unit: str,
    crit_temp: float,
    crit_temp_lower: float,
    unique_name: str,
) -> CheckGenerator:
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
    warn_upper_trend, crit_upper_trend = params.get('trend_levels', (None, None))
    if warn_upper_trend is None or crit_upper_trend is None:
        levels_upper_trend = None
    else:
        levels_upper_trend = (warn_upper_trend, crit_upper_trend)

    warn_lower_trend, crit_lower_trend = params.get("trend_levels_lower", (None, None))
    if warn_lower_trend is None or crit_lower_trend is None:
        levels_lower_trend = None
    else:
        # GUI representation of this parameter is labelled 'temperature decrease'; the user may input this
        # as a positive or negative value
        levels_lower_trend = (abs(warn_lower_trend) * -1, abs(crit_lower_trend) * -1)

    yield from check_levels(
        value=trend,
        levels_upper=levels_upper_trend,
        levels_lower=levels_lower_trend,
        label='Temperature trend',
        render_func=lambda trend: render_temp(
            trend,
            output_unit,
            relative=True,
            sign=True,
        ) + temp_unitsym[output_unit] + ' per ' + str(trend_range_min) + ' min',
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
        label='Time until temperature limit reached',
    )


# Checks Celsius temperature against crit/warn levels defined in params. temp must
# be int or float. Parameters:
# reading:           temperature reading of the device (per default interpreted as Celsius)
# params:            check parameters (pair or dict)
# unique_name:       unique name of this check, used for counters
# dev_unit:          unit of the device reading if this is not Celsius ("f": Fahrenheit, "k": Kelvin)
# dev_levels:        warn/crit levels of the device itself, if any. In the same unit as temp (dev_unit)
# dev_level_lower:   lower warn/crit device levels
# dev_status:        temperature state (0, 1, 2) as the device reports it (if applies)
# dev_status_name:   the device name (will be added in the check output)
# Note: you must not specify dev_status and dev_levels at the same time!


def _normalize_level(entry):
    """Collapse tuples containing only None to None itself.

    >>> _normalize_level(None)

    >>> _normalize_level((None, None))

    >>> _normalize_level((None, None, None, None))

    >>> _normalize_level((1, 2))
    (1, 2)

    """
    if isinstance(entry, tuple) and set(entry) <= {None}:
        return None
    return entry


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
                'levels': params[:2],
                'levels_lower': params[2:],  # type: ignore[typeddict-item]
            }
        else:
            params = {'levels': params[:2]}
    elif params is None:
        params = {}
    return params
