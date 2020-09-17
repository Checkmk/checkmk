#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Mapping, Optional, Tuple

import time

from ..agent_based_api.v1.type_defs import CheckResult, ValueStore

from ..agent_based_api.v1 import (
    check_levels,
    check_levels_predictive,
    get_average,
    Metric,
    regex,
    render,
    Result,
)


def core_name(orig: str, core_index: int) -> Tuple[str, str]:
    """
    normalize name of a cpu core so that the perfdata-template
    recognizes it. If the input name doesn't end on a number, this
    returns consecutive numbers per call so this function has to be
    called exactly once per core

        >>> core_name("cpu5", 2)
        ('cpu_core_util_5', 'cpu_core_util_average_5')
        >>> core_name("cpuaex", 15)
        ('cpu_core_util_15', 'cpu_core_util_average_15')

    """
    expr = regex(r"\d+$")
    match = expr.search(orig)
    if match is not None:
        num = match.group(0)
    else:
        # fallback: if the cores have odd names, use
        # consecutive numbers for each call
        num = str(core_index)
    return "cpu_core_util_%s" % num, "cpu_core_util_average_%s" % num


def check_cpu_util(
    value_store: ValueStore,
    util: float,
    params: Mapping,
    this_time: Optional[float] = None,
    cores=None,
    perf_max=100,
) -> CheckResult:
    # Convert legacy param style to new dict style
    if params is None:
        params = {}
    elif isinstance(params, tuple):
        params = {"util": params}

    if this_time is None:
        this_time = time.time()

    # Old/mixed config may look like:
    # {'util': (80.0, 90.0), 'levels': None}
    # 'levels is None' means: Do not impose levels
    # 'util' from default levels
    if "levels" in params and "util" in params:
        levels = params.get('levels')
    else:
        levels = params.get("util")
        if levels is None:  # legacy rules before 1.6
            levels = params.get("levels")

    warn, crit = levels if isinstance(levels, tuple) else (None, None)  # only for perfdata
    perfdata = [("util", util, warn, crit, 0, perf_max)]

    # Averaging
    if "average" in params:
        yield Metric("util", util, levels=(warn, crit), boundaries=(0, perf_max))
        value_checked = get_average(
            value_store,
            "cpu_utilization.avg",
            this_time,
            util,
            params["average"],
        )
        metric_name = "util_average"
        label = "Total CPU (%dmin average)" % params["average"]
        perfdata.append(("util_average", value_checked, warn, crit, 0, perf_max))
    else:
        value_checked = util
        metric_name = "util"
        label = "Total CPU"

    yield from check_levels_predictive(
        value_checked,
        metric_name=metric_name,
        levels=levels,
        render_func=render.percent,
        label=label,
    ) if isinstance(levels, dict) else check_levels(
        value_checked,
        metric_name=metric_name,
        levels_upper=levels,
        render_func=render.percent,
        label=label,
    )

    if "core_util_time_total" in params:
        threshold, warn, crit = params["core_util_time_total"]
        yield from cpu_util_time(this_time, "total", util, threshold, warn, crit)

    if cores and any([
            x in params for x in [
                "average_single",
                "core_util_graph",
                "core_util_time",
                "levels_single",
            ]
    ]):
        for core_index, (core, total_perc) in enumerate(cores):
            yield from _util_perfdata(core, total_perc, core_index, this_time, params, value_store)


def _check_single_core_util(
    util: float,
    metric: Optional[str],
    levels: Optional[Tuple[float, float]],
    label: str,
) -> CheckResult:
    for result in check_levels(
            util,
            levels_upper=levels,
            render_func=render.percent,
            label=label,
    ):
        yield Result(state=result.state, notice=result.summary)
    if metric:
        yield Metric(metric, util, levels=levels)


def _util_perfdata(core: str, total_perc: float, core_index: int, this_time: float, params: Mapping,
                   value_store: ValueStore) -> CheckResult:

    if "core_util_time" in params:
        threshold, warn, crit = params["core_util_time"]
        yield from cpu_util_time(this_time, core, total_perc, threshold, (warn, crit), value_store)

    config_single_avg = params.get('average_single', {})

    metric_names: Tuple[Optional[str], Optional[str]] = core_name(core, core_index)
    metric_raw, metric_avg = metric_names
    if not params.get("core_util_graph"):
        metric_raw = None
    if not config_single_avg.get('show_graph'):
        metric_avg = None

    if config_single_avg.get('apply_levels'):
        levels_raw = None
        levels_avg = params.get('levels_single')
    else:
        levels_raw = params.get('levels_single')
        levels_avg = None

    yield from _check_single_core_util(
        total_perc,
        metric_raw,
        levels_raw,
        "Core %s" % core,
    )

    time_avg = config_single_avg.get('time_average')
    if time_avg:
        yield from _check_single_core_util(
            get_average(
                value_store,
                "cpu_utilization_%d.avg" % core_index,
                this_time,
                total_perc,
                time_avg,
            ),
            metric_avg,
            levels_avg,
            "Core %s (%d-min average)" % (core, time_avg),
        )


#   .--helper--------------------------------------------------------------.
#   |                    _          _                                      |
#   |                   | |__   ___| |_ __   ___ _ __                      |
#   |                   | '_ \ / _ \ | '_ \ / _ \ '__|                     |
#   |                   | | | |  __/ | |_) |  __/ |                        |
#   |                   |_| |_|\___|_| .__/ \___|_|                        |
#   |                                |_|                                   |
#   '----------------------------------------------------------------------'


def cpu_util_time(
    this_time: float,
    core: str,
    perc: float,
    threshold: float,
    levels: Optional[Tuple[float, float]],
    value_store: ValueStore,
) -> CheckResult:
    core_states = value_store.get("cpu.util.core.high", {})
    if perc <= threshold:
        # drop core from states
        value_store["cpu.util.core.high"] = {k: v for k, v in core_states.items() if k != core}
        return

    timestamp = core_states.setdefault(core, this_time)
    value_store["cpu.util.core.high"] = core_states
    if timestamp == this_time:
        return

    yield from check_levels(
        this_time - timestamp,
        levels_upper=levels,
        render_func=render.timespan,
        label="%s is under high load for" % core,
    )
