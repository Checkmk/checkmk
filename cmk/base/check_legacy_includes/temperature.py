#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=unused-import

import time
from collections.abc import Generator, Sequence
from typing import AnyStr, NotRequired, TypedDict

from cmk.agent_based.legacy.v0_unstable import check_levels
from cmk.agent_based.v2 import get_average, get_rate, get_value_store, IgnoreResultsError
from cmk.plugins.lib.temperature import _migrate_params, TempParamDict
from cmk.plugins.lib.temperature import (
    fahrenheit_to_celsius as fahrenheit_to_celsius,  # ruff: ignore[unused-import]
)
from cmk.plugins.lib.temperature import render_temp as render_temp
from cmk.plugins.lib.temperature import StatusType as StatusType
from cmk.plugins.lib.temperature import temp_unitsym as temp_unitsym
from cmk.plugins.lib.temperature import TempParamType as TempParamType
from cmk.plugins.lib.temperature import to_celsius as to_celsius
from cmk.plugins.lib.temperature import TwoLevelsType as TwoLevelsType

Number = int | float

# ('foo', 5), ('foo', 5, 2, 7), ('foo', 5, None, None)
PerfDataEntryType = tuple[AnyStr, Number] | tuple[AnyStr, Number, Number | None]
PerfDataType = list[PerfDataEntryType]

# Generic Check Type. Can be used elsewhere too.
CheckType = tuple[StatusType, AnyStr, PerfDataType]


class CheckTempKwargs(TypedDict):
    dev_unit: NotRequired[str]
    dev_levels: NotRequired[TwoLevelsType | None]
    dev_levels_lower: NotRequired[TwoLevelsType | None]
    dev_status: NotRequired[StatusType | None]
    dev_status_name: NotRequired[str]


#################################################################################################
#
#                                 NOTE
#                           !! PLEASE READ !!
#
#       check_temperature_trend, check_temperature  and check_temperature_list have been
#       migrated to the new check API.
#       The functions below must be decomissioned (i.e. deleted) once all checks using
#       the check_temperature function have been migrated.
#
##################################################################################################


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


def check_temperature_determine_levels(  # pylint: disable=too-many-branches
    dlh,
    usr_warn,
    usr_crit,
    usr_warn_lower,
    usr_crit_lower,
    dev_warn,
    dev_crit,
    dev_warn_lower,
    dev_crit_lower,
):
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
        warn_lower, crit_lower = (
            minn(usr_warn_lower, dev_warn_lower),
            minn(usr_crit_lower, dev_crit_lower),
        )

    # Use most critical of your and device's levels
    elif dlh == "worst":
        warn, crit = minn(usr_warn, dev_warn), minn(usr_crit, dev_crit)
        warn_lower, crit_lower = (
            maxx(usr_warn_lower, dev_warn_lower),
            maxx(usr_crit_lower, dev_crit_lower),
        )

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


# determine temperature trends. This is a private function, not to be called by checks
def check_temperature_trend(  # pylint: disable=too-many-branches
    temp,
    params,
    output_unit,
    crit,
    crit_lower,
    unique_name,
):
    value_store = get_value_store()

    def combiner(status, infotext):
        if "status" in dir(combiner):
            combiner.status = max(combiner.status, status)  # type: ignore[attr-defined]
        else:
            combiner.status = status  # type: ignore[attr-defined]

        if "infotext" in dir(combiner):
            combiner.infotext += ", " + infotext  # type: ignore[attr-defined]
        else:
            combiner.infotext = infotext  # type: ignore[attr-defined]

    try:
        trend_range_min = params["period"]
        this_time = time.time()

        # first compute current rate in C/s by computing delta since last check
        rate = get_rate(
            get_value_store(),
            "temp.%s.delta" % unique_name,
            this_time,
            temp,
        )

        # average trend, initialize with zero (by default), rate_avg is in C/s
        rate_avg = get_average(
            value_store, f"temp.{unique_name}.trend", this_time, rate, trend_range_min
        )

        # rate_avg is growth in C/s, trend is in C per trend range minutes
        trend = float(rate_avg * trend_range_min * 60.0)
        sign = "+" if trend > 0 else ""
        combiner(0, f"rate: {sign}{render_temp(trend, output_unit, True)}/{trend_range_min:g} min")

        if "trend_levels" in params:
            warn_upper_trend, crit_upper_trend = params["trend_levels"]
        else:
            warn_upper_trend = crit_upper_trend = None
        # it may be unclear to the user if he should specify temperature decrease as a negative
        # number or positive. This works either way. Having a positive lower bound makes no
        # sense anyway.
        if "trend_levels_lower" in params:
            warn_lower_trend, crit_lower_trend = (abs(x) * -1 for x in params["trend_levels_lower"])
        else:
            warn_lower_trend = crit_lower_trend = None

        if crit_upper_trend is not None and trend > crit_upper_trend:
            combiner(
                2,
                f"rising faster than {render_temp(crit_upper_trend, output_unit, True)}/{trend_range_min:g} min(!!)",
            )
        elif warn_upper_trend is not None and trend > warn_upper_trend:
            combiner(
                1,
                f"rising faster than {render_temp(warn_upper_trend, output_unit, True)}/{trend_range_min:g} min(!)",
            )
        elif crit_lower_trend is not None and trend < crit_lower_trend:
            combiner(
                2,
                f"falling faster than {render_temp(crit_lower_trend, output_unit, True)}/{trend_range_min:g} min(!!)",
            )
        elif warn_lower_trend is not None and trend < warn_lower_trend:
            combiner(
                1,
                f"falling faster than {render_temp(warn_lower_trend, output_unit, True)}/{trend_range_min:g} min(!)",
            )

        if "trend_timeleft" in params:
            # compute time until temperature limit is reached
            # The start value of minutes_left is negative. The pnp graph and the perfometer
            # will interpret this as infinite -> not growing
            limit = crit if trend > 0 else crit_lower

            if limit:  # crit levels may not be set, especially lower level
                diff_to_limit = limit - temp
                if rate_avg != 0.0:
                    minutes_left = (diff_to_limit / rate_avg) / 60.0  # fixed: true-division
                else:
                    minutes_left = float("inf")

                def format_minutes(minutes):
                    if minutes > 60:  # hours
                        hours = int(minutes / 60.0)
                        minutes += -int(hours) * 60
                        return "%dh %02dm" % (hours, minutes)
                    return "%d minutes" % minutes

                warn, crit = params["trend_timeleft"]
                if minutes_left <= crit:
                    combiner(2, "%s until temp limit reached(!!)" % format_minutes(minutes_left))
                elif minutes_left <= warn:
                    combiner(1, "%s until temp limit reached(!)" % format_minutes(minutes_left))
    except IgnoreResultsError as e:
        combiner(3, str(e))
    return combiner.status, combiner.infotext  # type: ignore[attr-defined]


def check_temperature(  # pylint: disable=too-many-branches
    reading: Number,
    params: TempParamType,
    unique_name: AnyStr | None,
    dev_unit: AnyStr = "c",  # type: ignore[assignment]
    dev_levels: TwoLevelsType | None = None,
    dev_levels_lower: TwoLevelsType | None = None,
    dev_status: StatusType | None = None,
    dev_status_name: AnyStr = None,  # type: ignore[assignment]
) -> CheckType:
    """Check temperature levels and trends.

    The function will check the supplied data and supplied user configuration against the
    temperature reading and warn/crit on failed levels or trends.

    Args:
        reading (Number): The numeric temperature value itself.
        params (dict): A dictionary giving the user's configuration. See below.
        unique_name (str): The name under which to track perf-data.
        dev_unit (str): The unit. May be one of 'c', 'f' or 'k'. Default is 'c'.
        dev_levels (LevelsType | None): The upper levels (warn, crit)
        dev_levels_lower (LevelsType | None): The lower levels (warn, crit)
        dev_status (Number | None): The status according to the device itself.
        dev_status_name (AnyStr | None): What the device thinks the status should be called.

    Configuration:
        The parameter `params` may contain user configurable settings with the following keys:
            - ``input_unit`` -- The device's unit, user defined.
            - ``output_unit`` -- The unit by which to report.
            - ``levels`` -- Upper levels, user defined.
            - ``levels_lower`` -- Lower levels, user defined.
            - ``device_levels_handling`` -- One of the following modes:
                - ``usrdefault`` (default) -- Use user's levels, if not there use device's levels.
                - ``usr`` -- Always use user's levels. Ignore device's levels.
                - ``devdefault`` -- Use device's levels, if not there use user's levels.
                - ``dev`` -- Always use device's levels. Ignore users's levels.
                - ``best`` -- Report on the best case of user's and device's levels.
                - ``worst`` -- Report on the worst case of user's and device's levels.
            - ``trend_compute`` -- A dictionary of the following values:
                - ``period`` -- The observation period for trend computation in minutes.
                - ``trend_levels`` -- Levels on temp increase per period. (warn, crit)
                - ``trend_levels_lower`` -- Levels on temp decrease per period. (warn, crit)
                - ``trend_timeleft`` -- Levels on the time left until crit (upper or lower).

        The parameter `params` may also be one of the following legacy formats (do not use!):
            - None -- discarded
            - (None, None) -- discarded
            - (int|float, int|float) -- reused as params['levels']

    GUI:
         - cmk/gui/plugins/wato/check_parameters/temperature.py

    """
    # Convert legacy tuple params into new dict
    params = _migrate_params(params)

    # Convert reading into Celsius
    input_unit = params.get("input_unit", dev_unit)
    output_unit = params.get("output_unit", "c")
    temp = to_celsius(reading, input_unit)

    # Prepare levels, dealing with user defined and device's own levels
    usr_levels = _normalize_level(params.get("levels"))
    usr_levels_lower = _normalize_level(params.get("levels_lower"))
    dev_levels = _normalize_level(dev_levels)
    dev_levels_lower = _normalize_level(dev_levels_lower)

    # Set all user levels to None. None means do not impose a level
    usr_warn, usr_crit = usr_levels or (None, None)
    usr_warn_lower, usr_crit_lower = usr_levels_lower or (None, None)

    # Same for device levels
    dev_warn, dev_crit = to_celsius(dev_levels or (None, None), dev_unit)
    dev_warn_lower, dev_crit_lower = to_celsius(dev_levels_lower or (None, None), dev_unit)

    # Decide which of user's and device's levels should be used according to the setting
    # "device_levels_handling". Result is four variables: {warn,crit}{,_lower}
    dlh = params.get("device_levels_handling", "usrdefault")

    effective_levels = check_temperature_determine_levels(
        dlh,
        usr_warn,
        usr_crit,
        usr_warn_lower,
        usr_crit_lower,
        dev_warn,
        dev_crit,
        dev_warn_lower,
        dev_crit_lower,
    )

    if dlh == "usr" or (dlh == "usrdefault" and usr_levels):
        # ignore device status if user-levels are used
        dev_status = None

    # infotext does some device/user specifics
    status, _, perfdata = check_levels(
        temp,
        "temp",
        effective_levels,
    )

    # Render actual temperature, e.g. "17.8 °F"
    infotext = f"{render_temp(temp, output_unit)} {temp_unitsym[output_unit]}"

    # In case of a non-OK status output the information about the levels
    if status != 0:
        usr_levelstext = ""
        usr_levelstext_lower = ""
        dev_levelstext = ""
        dev_levelstext_lower = ""

        if usr_warn is not None and usr_crit is not None:
            usr_levelstext = f" (warn/crit at {render_temp(usr_warn, output_unit)}/{render_temp(usr_crit, output_unit)} {temp_unitsym[output_unit]})"

        if usr_warn_lower is not None and usr_crit_lower is not None:
            usr_levelstext_lower = f" (warn/crit below {render_temp(usr_warn_lower, output_unit)}/{render_temp(usr_crit_lower, output_unit)} {temp_unitsym[output_unit]})"

        if dev_levels:
            dev_levelstext = f" (device warn/crit at {render_temp(dev_warn, output_unit)}/{render_temp(dev_crit, output_unit)} {temp_unitsym[output_unit]})"

        if dev_levels_lower:
            dev_levelstext_lower = f" (device warn/crit below {render_temp(dev_warn_lower, output_unit)}/{render_temp(dev_crit_lower, output_unit)} {temp_unitsym[output_unit]})"

        # Output only levels that are relevant when computing the state
        if dlh == "usr":
            infotext += usr_levelstext + usr_levelstext_lower

        elif dlh == "dev":
            infotext += dev_levelstext + dev_levelstext_lower

        elif dlh in ("best", "worst"):
            infotext += (
                usr_levelstext + usr_levelstext_lower + dev_levelstext + dev_levelstext_lower
            )

        elif dlh == "devdefault":
            infotext += dev_levelstext + dev_levelstext_lower
            if not dev_levels:
                infotext += usr_levelstext
            if not dev_levels_lower:
                infotext += usr_levelstext_lower

        elif dlh == "usrdefault":
            infotext += usr_levelstext + usr_levelstext_lower
            if not usr_levels:
                infotext += dev_levelstext
            if not usr_levels_lower:
                infotext += dev_levelstext_lower

    if dev_status is not None:
        if dlh == "best":
            status = min(status, dev_status)
        else:
            status = max(status, dev_status)

    if dev_status is not None and dev_status != 0 and dev_status_name:  # omit status in OK case
        infotext += ", State on device: %s" % dev_status_name  # type: ignore[str-bytes-safe]

    # all checks specify a unique_name but when multiple sensors are handled through
    #   check_temperature_list, trend is only calculated for the average and then the individual
    #   calls to check_temperate receive no unique_name
    # "trend_compute" in params tells us if there if there is configuration for trend computation
    #   when activating trend computation through the website, "period" is always set together with
    #   the trend_compute dictionary. But a check may want to specify default levels for trends
    #   without activating them. In this case they can leave period unset to deactivate the
    #   feature.
    if unique_name and params.get("trend_compute", {}).get("period") is not None:
        crit = effective_levels[1]
        crit_lower = effective_levels[3]
        trend_status, trend_infotext = check_temperature_trend(
            temp, params["trend_compute"], output_unit, crit, crit_lower, unique_name
        )
        status = max(status, trend_status)
        if trend_infotext:
            infotext += ", " + trend_infotext

    return status, infotext, perfdata  # type: ignore[return-value]


# Wraps around check_temperature to check a list of sensors.
# sensorlist is a list of tuples:
# (subitem, temp, kwargs) or (subitem, temp)
# where subitem is a string (sensor-id)
# temp is a string, float or int temperature value
# and kwargs a dict of keyword arguments for check_temperature


def check_temperature_list(
    sensorlist: Sequence[tuple[str, Number, CheckTempKwargs]],
    params: TempParamDict,
) -> Generator[tuple[int, str, list[tuple[str, Number]]], None, None]:
    output_unit = params.get("output_unit", "c")

    if not sensorlist:
        return

    sensor_count = len(sensorlist)
    yield 0, f"Sensors: {sensor_count}", []

    unitsym = temp_unitsym[output_unit]
    tempmax = max(temp for _item, temp, _kwargs in sensorlist)
    yield 0, f"Highest: {render_temp(tempmax, output_unit)} {unitsym}", [("temp", tempmax)]
    tempavg = sum(temp for _item, temp, _kwargs in sensorlist) / float(sensor_count)
    yield 0, f"Average: {render_temp(tempavg, output_unit)} {unitsym}", []
    tempmin = min(temp for _item, temp, _kwargs in sensorlist)
    yield 0, f"Lowest: {render_temp(tempmin, output_unit)} {unitsym}", []

    for sub_item, temp, kwargs in sensorlist:
        sub_status, sub_infotext, _sub_perfdata = check_temperature(temp, params, None, **kwargs)
        if sub_status != 0:
            yield sub_status, f"{sub_item}: {sub_infotext}", []

    if "trend_compute" in params and "period" in params["trend_compute"]:
        usr_warn, usr_crit = params.get("levels") or (None, None)
        usr_warn_lower, usr_crit_lower = params.get("levels_lower") or (None, None)

        # no support for dev_unit or dev_levels in check_temperature_list so
        # this ignores the device level handling set in params
        _warn, crit, _warn_lower, crit_lower = check_temperature_determine_levels(
            "usr", usr_warn, usr_crit, usr_warn_lower, usr_crit_lower, None, None, None, None
        )

        trend_status, trend_infotext = check_temperature_trend(
            tempavg, params["trend_compute"], output_unit, crit, crit_lower, ""
        )
        if trend_infotext:
            yield trend_status, trend_infotext, []
