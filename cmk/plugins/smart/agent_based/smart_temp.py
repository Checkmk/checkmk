#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import time
from collections.abc import Mapping, MutableMapping
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_average,
    get_rate,
    get_value_store,
    IgnoreResultsError,
    Result,
    Service,
    State,
)
from cmk.plugins.lib.temperature import (
    OptFloat,
    render_temp,
    temp_unitsym,
    TempParamDict,
    to_celsius,
    TrendComputeDict,
)

# EXAMPLE DATA FROM: WDC SSC-D0128SC-2100
# <<<smart>>>
# /dev/sda ATA WDC_SSC-D0128SC-   1 Raw_Read_Error_Rate     0x000b   100   100   050    Pre-fail  Always       -       16777215
# /dev/sda ATA WDC_SSC-D0128SC-   3 Spin_Up_Time            0x0007   100   100   050    Pre-fail  Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC-   5 Reallocated_Sector_Ct   0x0013   100   100   050    Pre-fail  Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC-   7 Seek_Error_Rate         0x000b   100   100   050    Pre-fail  Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC-   9 Power_On_Hours          0x0012   100   100   000    Old_age   Always       -       1408
# /dev/sda ATA WDC_SSC-D0128SC-  10 Spin_Retry_Count        0x0013   100   100   050    Pre-fail  Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC-  12 Power_Cycle_Count       0x0012   100   100   000    Old_age   Always       -       523
# /dev/sda ATA WDC_SSC-D0128SC- 168 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       1
# /dev/sda ATA WDC_SSC-D0128SC- 175 Program_Fail_Count_Chip 0x0003   100   100   010    Pre-fail  Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC- 192 Power-Off_Retract_Count 0x0012   100   100   000    Old_age   Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC- 194 Temperature_Celsius     0x0022   040   100   000    Old_age   Always       -       40 (Lifetime Min/Max 30/60)
# /dev/sda ATA WDC_SSC-D0128SC- 197 Current_Pending_Sector  0x0012   100   100   000    Old_age   Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC- 240 Head_Flying_Hours       0x0013   100   100   050    Pre-fail  Always       -       0
# /dev/sda ATA WDC_SSC-D0128SC- 170 Unknown_Attribute       0x0003   100   100   010    Pre-fail  Always       -       1769478
# /dev/sda ATA WDC_SSC-D0128SC- 173 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       4217788040605


def discover_smart_temp(
    section: Mapping[str, Mapping[str, int]],
) -> DiscoveryResult:
    relevant = {"Temperature_Celsius", "Temperature_Internal", "Temperature"}
    for disk_name, disk in section.items():
        if relevant.intersection(disk):
            yield Service(item=disk_name)


def _check_trend(
    temp: float,
    params: TrendComputeDict,
    output_unit: str,
    crit: OptFloat,
    crit_lower: OptFloat,
    unique_name: str,
    value_store: MutableMapping[str, Any],
    now: float,
) -> CheckResult:
    trend_range_min = params["period"]

    # first compute current rate in C/s by computing delta since last check
    rate = get_rate(value_store, "temp.%s.delta" % unique_name, now, temp)

    # average trend, initialize with zero (by default), rate_avg is in C/s
    rate_avg = get_average(value_store, f"temp.{unique_name}.trend", now, rate, trend_range_min)

    # rate_avg is growth in C/s, trend is in C per trend range minutes
    trend = float(rate_avg * trend_range_min * 60.0)
    sign = "+" if trend > 0 else ""
    yield Result(
        state=State.OK,
        summary=f"rate: {sign}{render_temp(trend, output_unit, True)}/{trend_range_min:g} min",
    )

    warn_upper_trend, crit_upper_trend = params.get("trend_levels", (None, None))
    # it may be unclear to the user if he should specify temperature decrease as a negative
    # number or positive. This works either way. Having a positive lower bound makes no
    # sense anyway.
    warn_lower_trend: OptFloat = None
    crit_lower_trend: OptFloat = None
    match params.get("trend_levels_lower"):
        case (int() | float() as warn, int() | float() as crit):
            warn_lower_trend, crit_lower_trend = abs(warn) * -1, abs(crit) * -1
        case _:
            pass

    if crit_upper_trend is not None and trend > crit_upper_trend:
        yield Result(
            state=State.CRIT,
            summary=f"rising faster than {render_temp(crit_upper_trend, output_unit, True)}/{trend_range_min:g} min",
        )
    elif warn_upper_trend is not None and trend > warn_upper_trend:
        yield Result(
            state=State.WARN,
            summary=f"rising faster than {render_temp(warn_upper_trend, output_unit, True)}/{trend_range_min:g} min",
        )
    elif crit_lower_trend is not None and trend < crit_lower_trend:
        yield Result(
            state=State.CRIT,
            summary=f"falling faster than {render_temp(crit_lower_trend, output_unit, True)}/{trend_range_min:g} min",
        )
    elif warn_lower_trend is not None and trend < warn_lower_trend:
        yield Result(
            state=State.WARN,
            summary=f"falling faster than {render_temp(warn_lower_trend, output_unit, True)}/{trend_range_min:g} min",
        )

    if (timeleft := params.get("trend_timeleft")) is not None:
        # compute time until temperature limit is reached
        limit = crit if trend > 0 else crit_lower

        if limit:  # crit levels may not be set, especially lower level
            diff_to_limit = limit - temp
            minutes_left = diff_to_limit / rate_avg / 60.0 if rate_avg != 0.0 else float("inf")

            def format_minutes(minutes: float) -> str:
                if minutes > 60:  # hours
                    hours = int(minutes / 60.0)
                    minutes += -int(hours) * 60
                    return "%dh %02dm" % (hours, minutes)
                return "%d minutes" % minutes

            ml_warn, ml_crit = timeleft
            if ml_crit is not None and minutes_left <= ml_crit:
                yield Result(
                    state=State.CRIT,
                    summary="%s until temp limit reached" % format_minutes(minutes_left),
                )
            elif ml_warn is not None and minutes_left <= ml_warn:
                yield Result(
                    state=State.WARN,
                    summary="%s until temp limit reached" % format_minutes(minutes_left),
                )


def _check_temperature(
    reading: float,
    params: TempParamDict,
    unique_name: str,
    value_store: MutableMapping[str, Any],
    now: float,
) -> CheckResult:
    # Convert reading into Celsius
    input_unit = params.get("input_unit", "c")
    output_unit = params.get("output_unit", "c")
    temp = to_celsius(reading, input_unit)

    # Set all user levels to None. None means do not impose a level
    usr_warn, usr_crit = params.get("levels") or (None, None)
    usr_warn_lower, usr_crit_lower = params.get("levels_lower") or (None, None)

    # Decide which of user's and device's levels should be used according to the setting
    # "device_levels_handling". This plug-in reports no levels of its own, so "best" and
    # "worst" reduce to the user's levels, and "dev" to no levels at all.
    warn = crit = warn_lower = crit_lower = None
    dlh = params.get("device_levels_handling", "usrdefault")
    if dlh in ("usr", "best", "worst"):
        warn, crit, warn_lower, crit_lower = usr_warn, usr_crit, usr_warn_lower, usr_crit_lower
    elif dlh in ("usrdefault", "devdefault"):
        if usr_warn is not None and usr_crit is not None:
            warn, crit = usr_warn, usr_crit
        if usr_warn_lower is not None and usr_crit_lower is not None:
            warn_lower, crit_lower = usr_warn_lower, usr_crit_lower

    yield from check_levels(
        temp,
        "temp",
        (warn, crit, warn_lower, crit_lower),
        human_readable_func=lambda temp: (
            f"{render_temp(temp, output_unit)} {temp_unitsym[output_unit]}"
        ),
    )

    # when activating trend computation through the website, "period" is always set together
    # with the trend_compute dictionary. But a check may want to specify default levels for
    # trends without activating them. In this case they can leave period unset to deactivate
    # the feature.
    if (trend := params.get("trend_compute")) is not None and trend.get("period") is not None:
        try:
            yield from _check_trend(
                temp, trend, output_unit, crit, crit_lower, unique_name, value_store, now
            )
        except IgnoreResultsError as e:
            yield Result(state=State.UNKNOWN, summary=str(e))


def _check_smart_temp(
    item: str,
    params: TempParamDict,
    section: Mapping[str, Mapping[str, int]],
    value_store: MutableMapping[str, Any],
    now: float,
) -> CheckResult:
    if (data := section.get(item)) is None:
        return

    if (temperature := data.get("Temperature")) is None:
        return

    yield from _check_temperature(temperature, params, f"smart_{item}", value_store, now)


def check_smart_temp(
    item: str,
    params: TempParamDict,
    section: Mapping[str, Mapping[str, int]],
) -> CheckResult:
    yield from _check_smart_temp(item, params, section, get_value_store(), time.time())


check_plugin_smart_temp = CheckPlugin(
    name="smart_temp",
    service_name="Temperature SMART %s",
    sections=["smart"],  # This agent plugin was superseded by smart_posix
    discovery_function=discover_smart_temp,
    check_function=check_smart_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (35.0, 40.0)},
)
