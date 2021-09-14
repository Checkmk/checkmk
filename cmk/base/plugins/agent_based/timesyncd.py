#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Tuple, TypedDict

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


class Section(TypedDict, total=False):
    synctime: float
    server: str
    stratum: int
    offset: float
    jitter: float


def _get_seconds(time_string: str) -> float:
    if time_string.endswith("us"):
        return float(time_string[:-2]) / 1000000
    if time_string.endswith("ms"):
        return float(time_string[:-2]) / 1000
    if time_string.endswith("s"):
        return float(time_string[:-1])
    return float(time_string) / 1000000


def parse_timesyncd(string_table: StringTable) -> Section:
    section = Section()
    for line in string_table:
        if not line:
            continue

        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            section["synctime"] = float(line[0][3:-3])
            continue

        key = line[0].replace(":", "").lower()
        raw_str = line[1].replace("(", "").replace(")", "")

        if key == "server":
            section["server"] = raw_str
        if key == "stratum":
            section["stratum"] = int(raw_str)
        if key == "offset":
            section["offset"] = _get_seconds(raw_str)
        if key == "jitter":
            section["jitter"] = _get_seconds(raw_str)

    return section


def _get_levels_seconds(params):
    warn_milli, crit_milli = params.get("quality_levels", (None, None))
    if warn_milli and crit_milli:
        return warn_milli / 1000.0, crit_milli / 1000.0
    return None, None


def discover_timesyncd(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_timesyncd(params, section: Section) -> CheckResult:
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

    stratum_level = params.get("stratum_level") - 1
    stratum = section.get("stratum")
    if stratum is not None:
        yield from check_levels(
            value=stratum,
            levels_upper=(stratum_level, stratum_level),
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
