#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="arg-type"

import time
from collections.abc import Mapping
from typing import Generator, Literal, NotRequired, TypedDict

from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.check_legacy_includes.mem import check_memory_element
from cmk.base.config import check_info

from cmk.agent_based.v2 import get_average, get_value_store, render
from cmk.plugins.lib import memory

_MB = 1024**2

# Special memory and page file check for Windows


def inventory_mem_win(section):
    if "MemTotal" in section and "PageTotal" in section:
        yield None, {}


_Levels = (
    tuple[Literal["perc_used"], tuple[float, float]]
    | tuple[Literal["abs_free"], tuple[int, int]]
    | tuple[Literal["predictive"], Mapping[str, object]]
)


class Params(TypedDict):
    average: NotRequired[int]
    memory: _Levels
    pagefile: _Levels


def _do_averaging(
    timestamp: float,
    average_horizon_min: float,
    paramname: Literal["memory", "pagefile"],
    used: float,
    total: float,
) -> tuple[float, str]:
    used_avg = (
        get_average(
            get_value_store(),
            "mem.win.%s" % paramname,
            timestamp,
            used / 1024.0,  # use kB for compatibility
            average_horizon_min,
        )
        * 1024
    )
    return (
        used_avg,
        "%d min average: %s (%s)"
        % (
            average_horizon_min,
            render.percent(100.0 * used_avg / total),
            render.bytes(used_avg),
        ),
    )


def check_mem_windows(
    _no_item: None, params: Params, section: memory.SectionMem
) -> Generator[tuple[int, str, list], None, None]:
    now = time.time()

    for title, prefix, paramname, metric_name, levels in (
        ("RAM", "Mem", "memory", "mem_used", params["memory"]),
        ("Commit charge", "Page", "pagefile", "pagefile_used", params["pagefile"]),
    ):
        try:
            total = section["%sTotal" % prefix]
            free = section["%sFree" % prefix]
        except KeyError:
            continue
        # Metrics for total mem and pagefile are expected in MB
        yield 0, "", [(metric_name.replace("used", "total"), total / _MB)]

        used = float(total - free)

        average = params.get("average")

        state, infotext, perfdata = check_memory_element(
            title,
            used,
            total,
            None if average is not None or levels[0] == "predictive" else levels,
            metric_name=metric_name,
            create_percent_metric=title == "RAM",
        )

        # Do averaging, if configured, just for matching the levels
        if average is not None:
            used_avg, infoadd = _do_averaging(
                now,
                average,
                paramname,
                used,
                total,
            )
            infotext += f", {infoadd}"

            state, _infotext, perfadd = check_memory_element(
                title,
                used_avg,
                total,
                levels if levels[0] != "predictive" else None,
                metric_name=f"{metric_name}_avg",
            )
            perfdata += perfadd

        if levels[0] == "predictive":
            state, infoadd, perfadd = check_levels(
                used,
                metric_name,
                levels[1],
                infoname=title,
                human_readable_func=render.bytes,
            )
            infotext += ", " + infoadd
            perfdata += perfadd[1:]

        yield state, infotext, perfdata


check_info["mem.win"] = LegacyCheckDefinition(
    service_name="Memory",
    sections=["mem"],
    discovery_function=inventory_mem_win,
    check_function=check_mem_windows,
    check_ruleset_name="memory_pagefile_win",
    check_default_parameters=Params(
        memory=("perc_used", (80.0, 90.0)),
        pagefile=("perc_used", (80.0, 90.0)),
    ),
)
