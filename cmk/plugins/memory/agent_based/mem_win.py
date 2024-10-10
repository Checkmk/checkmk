#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import MutableMapping
from typing import Generic, NotRequired, TypedDict, TypeVar

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_average,
    get_value_store,
    LevelsT,
    Metric,
    render,
    Service,
)
from cmk.plugins.lib import memory

# Special memory and page file check for Windows


def discovery_mem_win(section: memory.SectionMem) -> DiscoveryResult:
    if "MemTotal" in section and "PageTotal" in section:
        yield Service()


_NumberT = TypeVar("_NumberT", int, float)


class _DualLevels(TypedDict, Generic[_NumberT]):
    lower: LevelsT[_NumberT]
    upper: LevelsT[_NumberT]


class _Levels(TypedDict):
    perc_used: NotRequired[_DualLevels[float]]
    abs_free: NotRequired[_DualLevels[int]]
    abs_used: NotRequired[_DualLevels[int]]


class Params(TypedDict):
    average: NotRequired[float]
    memory: _Levels
    pagefile: _Levels


_NO_LEVELS = _DualLevels(lower=("no_levels", None), upper=("no_levels", None))


def check_mem_windows(params: Params, section: memory.SectionMem) -> CheckResult:
    yield from check_mem_windows_static(
        params=params, section=section, value_store=get_value_store(), now=time.time()
    )


def check_mem_windows_static(
    *,
    params: Params,
    section: memory.SectionMem,
    value_store: MutableMapping[str, object],
    now: float,
) -> CheckResult:
    averaging_horizon_seconds = params.get("average")

    for title, prefix, metric_prefix, levels in (
        ("RAM", "Mem", "mem", params["memory"]),
        ("Virtual memory", "Page", "pagefile", params["pagefile"]),
    ):
        try:
            total = section["%sTotal" % prefix]
            free_raw = section["%sFree" % prefix]
        except KeyError:
            continue
        used_raw = float(total - free_raw)

        # We want to use memory.check_element to get the nice standardized output,
        # but we also want to use check_levels for predictive levels support.
        # For the latter we may or may not want to do averaging.
        # Least confusing way to do this is to yield the generic check_element first,
        # then create all the metrics, and finally check the levels.
        yield from memory.check_element(label=title, used=used_raw, total=total)

        # Do averaging, if configured, just for matching the levels
        if averaging_horizon_seconds is None:
            used = used_raw
            avg_text = ""
            avg_suffix = ""
        else:
            used = get_average(
                value_store,
                metric_prefix,
                now,
                used_raw,
                averaging_horizon_seconds / 60,
            )
            avg_text = f" (averaged over {render.timespan(averaging_horizon_seconds)})"
            avg_suffix = "_avg"
            yield Metric(
                f"{metric_prefix}_used_percent", used_raw / total * 100.0, boundaries=(0.0, 100.0)
            )
            yield Metric(f"{metric_prefix}_used", used_raw, boundaries=(0.0, total))
            yield Metric(f"{metric_prefix}_free", free_raw, boundaries=(0.0, total))

        free = total - used

        abs_free = levels.get("abs_free", _NO_LEVELS)
        abs_used = levels.get("abs_used", _NO_LEVELS)
        perc_used = levels.get("perc_used", _NO_LEVELS)

        yield from check_levels(
            used / total * 100.0,
            label=f"Used{avg_text}",
            levels_lower=perc_used["lower"],
            levels_upper=perc_used["upper"],
            render_func=render.percent,
            metric_name=f"{metric_prefix}_used_percent{avg_suffix}",
            notice_only=True,
        )
        yield from check_levels(
            used,
            label=f"Used{avg_text}",
            levels_lower=abs_used["lower"],
            levels_upper=abs_used["upper"],
            render_func=render.bytes,
            metric_name=f"{metric_prefix}_used{avg_suffix}",
            notice_only=True,
        )
        yield from check_levels(
            free,
            label=f"Free{avg_text}",
            levels_lower=abs_free["lower"],
            levels_upper=abs_free["upper"],
            render_func=render.bytes,
            metric_name=f"{metric_prefix}_free{avg_suffix}",
            notice_only=True,
        )


check_plugin_mem_win = CheckPlugin(
    name="mem_win",
    service_name="Memory",
    sections=["mem"],
    discovery_function=discovery_mem_win,
    check_function=check_mem_windows,
    check_ruleset_name="memory_pagefile_win",
    check_default_parameters=Params(
        memory=_Levels(
            perc_used=_DualLevels(
                lower=("no_levels", None),
                upper=("fixed", (80.0, 90.0)),
            ),
        ),
        pagefile=_Levels(
            perc_used=_DualLevels(
                lower=("no_levels", None),
                upper=("fixed", (80.0, 90.0)),
            ),
        ),
    ),
)
