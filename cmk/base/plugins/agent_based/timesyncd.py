#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
import time
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence, Tuple, TypedDict

from .agent_based_api.v1 import (
    check_levels,
    get_value_store,
    register,
    render,
    Result,
    Service,
    State,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.timesync import tolerance_check


class CheckParams(TypedDict):
    stratum_level: int
    quality_levels: Tuple[float, float]
    alert_delay: Tuple[int, int]
    last_synchronized: Tuple[int, int]


# last_synchronized default values increased since a few systems required longer time
default_check_parameters = CheckParams(
    stratum_level=10,
    quality_levels=(200.0, 500.0),
    alert_delay=(300, 3600),
    last_synchronized=(7500, 10800),
)


@dataclass(frozen=True)
class _TimeUnit:
    text_representations: Sequence[str]
    multiple_of_seconds: float


_UNITS_TO_SECONDS = {
    unit: time_unit.multiple_of_seconds
    for time_unit in [
        _TimeUnit(["y", "year", "years"], 31557600),
        _TimeUnit(["M", "month, months"], 2630016),
        _TimeUnit(["w", "week", "weeks"], 604800),
        _TimeUnit(["d", "day", "days"], 86400),
        _TimeUnit(["h", "hour", "hours"], 3600),
        _TimeUnit(["m", "min", "minute", "minutes"], 60),
        _TimeUnit(["s", "sec", "second", "seconds"], 1),
        _TimeUnit(["msec", "ms"], 1e-3),
        _TimeUnit(["µs", "usec", "us"], 1e-6),
    ]
    for unit in time_unit.text_representations
}


class Section(TypedDict, total=False):
    synctime: float
    server: str
    stratum: int
    offset: float
    jitter: float


def _strip_sign(time_string: str) -> Tuple[str, int]:
    if time_string[0] == "-":
        return time_string[1:], -1
    if time_string[0] == "+":
        return time_string[1:], 1

    return time_string, 1


def _split_into_components(time_string: str) -> Iterable[float]:
    if time_string[-1].isdigit():  # 3h18 -> 3h18s
        time_string += "s"

    split_at_numbers = re.split("([0-9]*[.]?[0-9]+)", time_string)[1:]
    for value_str, unit in zip(split_at_numbers[::2], split_at_numbers[1::2]):
        yield float(value_str) * _UNITS_TO_SECONDS[unit]


def _get_seconds(time_components: Iterable[str]) -> float:
    """
    Convert a systemd time span to seconds.

    See systemd.time(7) for a detailed description of the format.

    >>> _get_seconds(["1h30m2s90us"])
    5402.00009
    >>> _get_seconds(["-2h15"])
    -7215.0
    >>> _get_seconds(["-2y","5M","2w","8d","9h","1min","53.991us"])
    -78198540.00005399
    """
    time_string = "".join(time_components)
    time_string, sign = _strip_sign(time_string)
    return sign * sum(_split_into_components(time_string))  # type: ignore


def parse_timesyncd(string_table: StringTable) -> Section:
    section = Section()
    for line in string_table:
        if not line:
            continue

        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            section["synctime"] = float(line[0][3:-3])
            continue

        key = line[0].replace(":", "").lower()

        if key == "server":
            section["server"] = line[1].replace("(", "").replace(")", "")
        if key == "stratum":
            section["stratum"] = int(line[1])
        if key == "offset":
            section["offset"] = _get_seconds(line[1:])
        if key == "jitter":
            section["jitter"] = _get_seconds(line[1:])

    return section


def _get_levels_seconds(params: Mapping[str, Any]) -> Tuple[float, float]:
    warn_milli, crit_milli = params["quality_levels"]
    return warn_milli / 1000.0, crit_milli / 1000.0


def discover_timesyncd(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_timesyncd(params: Mapping[str, Any], section: Section) -> CheckResult:
    levels = _get_levels_seconds(params)

    # Offset information
    offset = section.get("offset")
    if offset is not None:
        yield from check_levels(
            value=abs(offset),
            metric_name="time_offset",
            levels_upper=levels,
            render_func=render.timespan,
            label="Offset",
        )

    synctime = section.get("synctime")
    # either set the sync time, and yield nothing OR
    # check for how long we've been seeing None as sync time
    yield from tolerance_check(
        set_sync_time=synctime,
        levels_upper=params.get("alert_delay"),
        now=time.time(),
        value_store=get_value_store(),
    )
    if synctime is not None:
        # now we have set it, but not yet checked it. Check it!
        yield from tolerance_check(
            set_sync_time=None,  # use the time we just set.
            levels_upper=params.get("last_synchronized"),
            now=time.time(),
            value_store=get_value_store(),
        )

    server = section.get("server")
    if server is None or server == "null":
        yield Result(state=State.OK, summary="Found no time server")
        return

    if (stratum := section.get("stratum")) is not None:
        yield from check_levels(
            value=stratum,
            levels_upper=(stratum_level := params["stratum_level"] - 1, stratum_level),
            label="Stratum",
        )

    # Jitter Information append
    jitter = section.get("jitter")
    if jitter is not None:
        yield from check_levels(
            value=jitter,
            metric_name="jitter",
            levels_upper=levels,
            render_func=render.datetime,
            label="Jitter",
        )

    yield Result(state=State.OK, summary="Synchronized on %s" % server)


register.agent_section(
    name="timesyncd",
    parse_function=parse_timesyncd,
)

register.check_plugin(
    name="timesyncd",
    service_name="Systemd Timesyncd Time",
    discovery_function=discover_timesyncd,
    check_function=check_timesyncd,
    check_default_parameters=default_check_parameters,
    check_ruleset_name="timesyncd_time",
)
