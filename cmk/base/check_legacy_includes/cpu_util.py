#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

from cmk.agent_based.legacy.v0_unstable import check_levels
from cmk.agent_based.v2 import (
    get_average,
    get_value_store,
    render,
)
from cmk.plugins.lib import cpu_util

# Common file for all (modern) checks that check CPU utilization (not load!)

# Example for check parameters:
# 1. Variant: Tuple (warn, crit). This is legacy style
# 2. Variant: dictionary:
#
#  param = {
#     "util" : .... --> compatible with check_levels(), optional
#     "average" : 15 # -> compute average for 15 minutes, optional
#   }

##########################################################################################
##########################################################################################
##########################################################################################
#                                                                                        #
#     THE FUNCTIONS IN THIS FILE HAVE PARTIALLY BEEN MIGRATED TO CPU_UTIL.PY             #
#     IN cmk.plugins.lib/                                             #
#                                                                                        #
#     PLEASE TAKE A LOOK AT THOSE BEFOR MODIFYING ANY CODE IN THIS FILE                  #
#     THERE ARE MORE FUNCTIONS IN IT THAT THE ONES USED BELOW!                           #
#                                                                                        #

cpu_util_core_name = cpu_util.core_name
CPUInfo = cpu_util.CPUInfo

#                                                                                        #
##########################################################################################
##########################################################################################
##########################################################################################


# ALREADY MIGRATED
def check_cpu_util(util, params, this_time=None, cores=None, perf_max=100):
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
        levels = params.get("levels")
    else:
        levels = params.get("util")
        if levels is None:  # legacy rules before 1.6
            levels = params.get("levels")

    warn, crit = levels if isinstance(levels, tuple) else (None, None)  # only for perfdata
    perfdata = [("util", util, warn, crit, 0, perf_max)]

    # Averaging
    if "average" in params:
        util_avg = get_average(
            get_value_store(), "cpu_utilization.avg", this_time, util, params["average"]
        )
        perfdata.append(("util_average", util_avg, warn, crit, 0, perf_max))
        state, infotext, extraperf = check_levels(
            util_avg,
            "util_average",
            levels,
            human_readable_func=render.percent,
            infoname="Total CPU (%dmin average)" % params["average"],
        )
    else:
        state, infotext, extraperf = check_levels(
            util,
            "util",
            levels,
            human_readable_func=render.percent,
            infoname="Total CPU",
        )

    perfdata += extraperf[1:]  # type: ignore[arg-type] # reference curve for predictive levels
    yield state, infotext, perfdata

    if "core_util_time_total" in params:
        threshold, warn, crit = params["core_util_time_total"]
        yield _cpu_util_time(this_time, "total", util, threshold, warn, crit)

    if cores and any(
        x in params
        for x in [
            "average_single",
            "core_util_graph",
            "core_util_time",
            "levels_single",
        ]
    ):
        for core_index, (core, total_perc) in enumerate(cores):
            yield from _util_perfdata(core, total_perc, core_index, this_time, params)


# ALREADY MIGRATED
def _check_single_core_util(util, metric, levels, infoname):
    state, infotext, perfdata = check_levels(
        util,
        metric,
        levels,
        human_readable_func=render.percent,
        infoname=infoname,
    )
    if not state:
        infotext = ""
    if infotext or perfdata:
        yield state, infotext, perfdata


# ALREADY MIGRATED
def _util_perfdata(core, total_perc, core_index, this_time, params):
    if "core_util_time" in params:
        threshold, warn, crit = params["core_util_time"]
        yield _cpu_util_time(this_time, core, total_perc, threshold, warn, crit)

    config_single_avg = params.get("average_single", {})

    metric_raw: str | None
    metric_avg: str | None
    metric_raw, metric_avg = cpu_util_core_name(core, core_index)
    if not params.get("core_util_graph"):
        metric_raw = None
    if not config_single_avg.get("show_graph"):
        metric_avg = None

    if config_single_avg.get("apply_levels"):
        levels_raw = None
        levels_avg = params.get("levels_single")
    else:
        levels_raw = params.get("levels_single")
        levels_avg = None

    yield from _check_single_core_util(
        total_perc,
        metric_raw,
        levels_raw,
        "Core %s" % core,
    )

    time_avg = config_single_avg.get("time_average")
    if time_avg:
        yield from _check_single_core_util(
            get_average(
                get_value_store(),
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


# ALREADY MIGRATED
def _cpu_util_time(this_time, core, perc, threshold, warn_core, crit_core):
    core_state_name = "cpu.util.core.high.%s" % core
    value_store = get_value_store()
    if perc > threshold:
        timestamp = value_store.get(core_state_name, 0)
        high_load_duration = this_time - timestamp
        state, infotext, _ = check_levels(
            high_load_duration,
            "%s_is_under_high_load_for" % core,  # Not used
            (warn_core, crit_core),
            human_readable_func=render.timespan,
            infoname="%s is under high load for" % core,
        )
        if timestamp == 0:
            value_store[core_state_name] = this_time
        elif state:
            return state, infotext, []
        return 0, "", []

    value_store.pop(core_state_name, None)
    return 0, "", []
