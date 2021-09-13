#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
import time
from typing import AnyStr, List, Optional, Tuple, Union

from cmk.base.check_api import check_levels, get_average, get_rate, MKCounterWrapped, state_markers
from cmk.base.plugins.agent_based.utils.temperature import (  # pylint: disable=unused-import; # reimported from checks!; See warning below
    _migrate_params,
    fahrenheit_to_celsius,
    render_temp,
    StatusType,
    temp_unitsym,
    TempParamType,
    to_celsius,
    TwoLevelsType,
)

Number = Union[int, float]

# ('foo', 5), ('foo', 5, 2, 7), ('foo', 5, None, None)
PerfDataEntryType = Union[Tuple[AnyStr, Number], Tuple[AnyStr, Number, Optional[Number]]]
PerfDataType = List[PerfDataEntryType]

# Generic Check Type. Can be used elsewhere too.
CheckType = Tuple[StatusType, AnyStr, PerfDataType]

#################################################################################################
#
#                                 NOTE
#                           !! PLEASE READ !!
#
#       check_temperature_list has NOT been migrated to the new check API yet.
#
#       check_temperature_trend and check_temperature have been migrated to the new check API.
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


def check_temperature_determine_levels(
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
        warn_lower, crit_lower = minn(usr_warn_lower, dev_warn_lower), minn(
            usr_crit_lower, dev_crit_lower
        )

    # Use most critical of your and device's levels
    elif dlh == "worst":
        warn, crit = minn(usr_warn, dev_warn), minn(usr_crit, dev_crit)
        warn_lower, crit_lower = maxx(usr_warn_lower, dev_warn_lower), maxx(
            usr_crit_lower, dev_crit_lower
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
def check_temperature_trend(temp, params, output_unit, crit, crit_lower, unique_name):
    def combiner(status, infotext):
        if "status" in dir(combiner):
            combiner.status = max(combiner.status, status)
        else:
            combiner.status = status

        if "infotext" in dir(combiner):
            combiner.infotext += ", " + infotext
        else:
            combiner.infotext = infotext

    try:
        trend_range_min = params["period"]
        this_time = time.time()

        # first compute current rate in C/s by computing delta since last check
        rate = get_rate("temp.%s.delta" % unique_name, this_time, temp, allow_negative=True)

        # average trend, initialize with zero (by default), rate_avg is in C/s
        rate_avg = get_average("temp.%s.trend" % unique_name, this_time, rate, trend_range_min)

        # rate_avg is growth in C/s, trend is in C per trend range minutes
        trend = float(rate_avg * trend_range_min * 60.0)
        sign = "+" if trend > 0 else ""
        combiner(
            0, "rate: %s%s/%g min" % (sign, render_temp(trend, output_unit, True), trend_range_min)
        )

        if "trend_levels" in params:
            warn_upper_trend, crit_upper_trend = params["trend_levels"]
        else:
            warn_upper_trend = crit_upper_trend = None
        # it may be unclear to the user if he should specify temperature decrease as a negative
        # number or positive. This works either way. Having a positive lower bound makes no
        # sense anyway.
        if "trend_levels_lower" in params:
            warn_lower_trend, crit_lower_trend = [abs(x) * -1 for x in params["trend_levels_lower"]]
        else:
            warn_lower_trend = crit_lower_trend = None

        if crit_upper_trend is not None and trend > crit_upper_trend:
            combiner(
                2,
                "rising faster than %s/%g min(!!)"
                % (render_temp(crit_upper_trend, output_unit, True), trend_range_min),
            )
        elif warn_upper_trend is not None and trend > warn_upper_trend:
            combiner(
                1,
                "rising faster than %s/%g min(!)"
                % (render_temp(warn_upper_trend, output_unit, True), trend_range_min),
            )
        elif crit_lower_trend is not None and trend < crit_lower_trend:
            combiner(
                2,
                "falling faster than %s/%g min(!!)"
                % (render_temp(crit_lower_trend, output_unit, True), trend_range_min),
            )
        elif warn_lower_trend is not None and trend < warn_lower_trend:
            combiner(
                1,
                "falling faster than %s/%g min(!)"
                % (render_temp(warn_lower_trend, output_unit, True), trend_range_min),
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
    except MKCounterWrapped:
        pass
    return combiner.status, combiner.infotext


def check_temperature(
    reading: Number,
    params: TempParamType,
    unique_name: Optional[AnyStr],
    dev_unit: AnyStr = "c",
    dev_levels: Optional[TwoLevelsType] = None,
    dev_levels_lower: Optional[TwoLevelsType] = None,
    dev_status: Optional[StatusType] = None,
    dev_status_name: AnyStr = None,
) -> CheckType:
    """Check temperature levels and trends.

    The function will check the supplied data and supplied user configuration against the
    temperature reading and warn/crit on failed levels or trends.

    Args:
        reading (Number): The numeric temperature value itself.
        params (dict): A dictionary giving the user's configuration. See below.
        unique_name (str): The name under which to track perf-data.
        dev_unit (str): The unit. May be one of 'c', 'f' or 'k'. Default is 'c'.
        dev_levels (Optional[LevelsType]): The upper levels (warn, crit)
        dev_levels_lower (Optional[LevelsType]): The lower levels (warn, crit)
        dev_status (Optional[Number]): The status according to the device itself.
        dev_status_name (Optional[AnyStr]): What the device thinks the status should be called.

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
    status, _, perfdata = check_levels(  # type: ignore[name-defined]
        temp,
        "temp",
        effective_levels,
    )

    if dev_status is not None:
        if dlh == "best":
            status = min(status, dev_status)
        else:
            status = max(status, dev_status)

    # Render actual temperature, e.g. "17.8 °F"
    infotext = "%s %s" % (render_temp(temp, output_unit), temp_unitsym[output_unit])

    if dev_status is not None and dev_status != 0 and dev_status_name:  # omit status in OK case
        infotext += ", %s" % dev_status_name

    # In case of a non-OK status output the information about the levels
    if status != 0:
        usr_levelstext = ""
        usr_levelstext_lower = ""
        dev_levelstext = ""
        dev_levelstext_lower = ""

        if usr_warn is not None and usr_crit is not None:
            usr_levelstext = " (warn/crit at %s/%s %s)" % (
                render_temp(usr_warn, output_unit),
                render_temp(usr_crit, output_unit),
                temp_unitsym[output_unit],
            )

        if usr_warn_lower is not None and usr_crit_lower is not None:
            usr_levelstext_lower = " (warn/crit below %s/%s %s)" % (
                render_temp(usr_warn_lower, output_unit),
                render_temp(usr_crit_lower, output_unit),
                temp_unitsym[output_unit],
            )

        if dev_levels:
            dev_levelstext = " (device warn/crit at %s/%s %s)" % (
                render_temp(dev_warn, output_unit),
                render_temp(dev_crit, output_unit),
                temp_unitsym[output_unit],
            )

        if dev_levels_lower:
            dev_levelstext_lower = " (device warn/crit below %s/%s %s)" % (
                render_temp(dev_warn_lower, output_unit),
                render_temp(dev_crit_lower, output_unit),
                temp_unitsym[output_unit],
            )

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

    return status, infotext, perfdata


# Wraps around check_temperature to check a list of sensors.
# sensorlist is a list of tuples:
# (subitem, temp, kwargs) or (subitem, temp)
# where subitem is a string (sensor-id)
# temp is a string, float or int temperature value
# and kwargs a dict of keyword arguments for check_temperature


def check_temperature_list(sensorlist, params, unique_name):
    params = _migrate_params(params)

    output_unit = params.get("output_unit", "c")

    def worststate(a, b):
        if a != 3 and b != 3:
            return max(a, b)
        if a != 2 and b != 2:
            return 3
        return 2

    if sensorlist == []:
        return

    sensor_count = len(sensorlist)
    tempsum = 0
    tempmax = sensorlist[0][1]
    tempmin = sensorlist[0][1]
    status = 0
    detailtext = ""
    for entry in sensorlist:

        if len(entry) == 2:
            sub_item, temp = entry
            kwargs = {}
        else:
            sub_item, temp, kwargs = entry
        if not isinstance(temp, (float, int)):
            temp = float(temp)

        tempsum += temp
        tempmax = max(tempmax, temp)
        tempmin = min(tempmin, temp)
        sub_status, sub_infotext, _sub_perfdata = check_temperature(temp, params, None, **kwargs)
        status = worststate(status, sub_status)
        if status != 0:
            detailtext += sub_item + ": " + sub_infotext + state_markers[sub_status] + ", "
    if detailtext:
        detailtext = " " + detailtext[:-2]  # Drop trailing ", ", add space to join with summary

    unitsym = temp_unitsym[output_unit]
    tempavg = tempsum / float(sensor_count)
    summarytext = "%d Sensors; Highest: %s %s, Average: %s %s, Lowest: %s %s" % (
        sensor_count,
        render_temp(tempmax, output_unit),
        unitsym,
        render_temp(tempavg, output_unit),
        unitsym,
        render_temp(tempmin, output_unit),
        unitsym,
    )
    infotext = summarytext + detailtext
    perfdata = [("temp", tempmax)]

    if "trend_compute" in params and "period" in params["trend_compute"]:
        usr_warn, usr_crit = params.get("levels") or (None, None)
        usr_warn_lower, usr_crit_lower = params.get("levels_lower") or (None, None)

        # no support for dev_unit or dev_levels in check_temperature_list so
        # this ignores the device level handling set in params
        _warn, crit, _warn_lower, crit_lower = check_temperature_determine_levels(
            "usr", usr_warn, usr_crit, usr_warn_lower, usr_crit_lower, None, None, None, None
        )

        trend_status, trend_infotext = check_temperature_trend(
            tempavg, params["trend_compute"], output_unit, crit, crit_lower, unique_name
        )
        status = max(status, trend_status)
        if trend_infotext:
            infotext += ", " + trend_infotext

    return status, infotext, perfdata
