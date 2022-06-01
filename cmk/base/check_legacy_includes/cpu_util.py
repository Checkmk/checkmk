#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import cmk.base.plugins.agent_based.utils.cpu_util as cpu_util
from cmk.base.check_api import (
    check_levels,
    clear_item_state,
    get_age_human_readable,
    get_average,
    get_item_state,
    get_percent_human_readable,
    get_rate,
    MKCounterWrapped,
    set_item_state,
)

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
#     IN cmk/base/plugins/agent_based/utils/                                             #
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
def util_counter(stats: CPUInfo, this_time: float) -> CPUInfo:
    # Compute jiffi-differences of all relevant counters
    diff_values = []
    for n, v in enumerate(stats[1:], start=1):
        countername = "cpu.util.%d" % n
        last_val = get_item_state(countername, (0, 0))[1]
        diff_values.append(v - last_val)
        set_item_state(countername, (this_time, v))

    return CPUInfo(stats.name, *diff_values)


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
        util_avg = get_average("cpu_utilization.avg", this_time, util, params["average"])
        perfdata.append(("util_average", util_avg, warn, crit, 0, perf_max))
        state, infotext, extraperf = check_levels(
            util_avg,
            "util_average",
            levels,
            human_readable_func=get_percent_human_readable,
            infoname="Total CPU (%dmin average)" % params["average"],
        )
    else:
        state, infotext, extraperf = check_levels(
            util,
            "util",
            levels,
            human_readable_func=get_percent_human_readable,
            infoname="Total CPU",
        )

    perfdata += extraperf[1:]  # type: ignore[arg-type] # reference curve for predictive levels
    yield state, infotext, perfdata

    if "core_util_time_total" in params:
        threshold, warn, crit = params["core_util_time_total"]
        yield cpu_util_time(this_time, "total", util, threshold, warn, crit)

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
def check_cpu_util_unix(values: CPUInfo, params, cores=None, values_counter=True):
    this_time = time.time()
    if values_counter:
        diff_values = util_counter(values, this_time)
        sum_jiffies = diff_values.total_sum
        if sum_jiffies == 0:
            raise MKCounterWrapped("Too short time difference since last check")
        (
            user_perc,
            system_perc,
            wait_perc,
            steal_perc,
            guest_perc,
            util_total_perc,
        ) = diff_values.utils_perc
    else:
        user_perc = values.user
        system_perc = values.system
        wait_perc = values.iowait
        steal_perc = values.steal
        guest_perc = values.guest
        util_total_perc = values.util_total

    yield check_levels(
        user_perc, "user", None, human_readable_func=get_percent_human_readable, infoname="User"
    )
    yield check_levels(
        system_perc,
        "system",
        None,
        human_readable_func=get_percent_human_readable,
        infoname="System",
    )
    yield check_levels(
        wait_perc,
        "wait",
        params.get("iowait"),
        human_readable_func=get_percent_human_readable,
        infoname="Wait",
    )

    # Compute values used in virtualized environments (Xen, etc.)
    # Only do this for counters that have counted at least one tick
    # since the system boot. This avoids silly output in systems
    # where these counters are not being used
    if values.steal:
        yield check_levels(
            steal_perc,
            "steal",
            params.get("steal"),
            human_readable_func=get_percent_human_readable,
            infoname="Steal",
        )

    if values.guest:
        yield check_levels(
            guest_perc,
            "guest",
            None,
            human_readable_func=get_percent_human_readable,
            infoname="Guest",
        )

    summary_cores = []
    if cores:
        for core in cores:
            prev_total = get_item_state("cpu.util.%s.total" % core.name, 0)
            util_total = core.util_total
            total_diff = util_total - prev_total
            set_item_state("cpu.util.%s.total" % core.name, util_total)
            total_perc = (100.0 * total_diff / sum_jiffies) * len(cores)
            summary_cores.append((core.name, total_perc))

    for check_result in check_cpu_util(
        util_total_perc, params, this_time, summary_cores, perf_max=None
    ):
        yield check_result


# ALREADY MIGRATED
def _check_single_core_util(util, metric, levels, infoname):
    state, infotext, perfdata = check_levels(
        util,
        metric,
        levels,
        human_readable_func=get_percent_human_readable,
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
        yield cpu_util_time(this_time, core, total_perc, threshold, warn, crit)

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
                "cpu_utilization_%d.avg" % core_index,
                this_time,
                total_perc,
                time_avg,
            ),
            metric_avg,
            levels_avg,
            "Core %s (%d-min average)" % (core, time_avg),
        )


# not yet migrated!
def check_cpu_util_linux_container(_no_item, params, parsed):
    con_ticks = parsed.get("container_ticks")
    sys_ticks = parsed.get("system_ticks")
    num_cpus = parsed.get("num_cpus")
    if None in (con_ticks, sys_ticks, num_cpus):
        return None

    cpu_tick_rate = get_rate("container_ticks", sys_ticks, con_ticks)

    cpu_usage = cpu_tick_rate * num_cpus * 100.0

    return check_cpu_util(cpu_usage, params, perf_max=num_cpus * 100)


#   .--helper--------------------------------------------------------------.
#   |                    _          _                                      |
#   |                   | |__   ___| |_ __   ___ _ __                      |
#   |                   | '_ \ / _ \ | '_ \ / _ \ '__|                     |
#   |                   | | | |  __/ | |_) |  __/ |                        |
#   |                   |_| |_|\___|_| .__/ \___|_|                        |
#   |                                |_|                                   |
#   '----------------------------------------------------------------------'


# ALREADY MIGRATED
def cpu_util_time(this_time, core, perc, threshold, warn_core, crit_core):
    core_state_name = "cpu.util.core.high.%s" % core
    if perc > threshold:
        timestamp = get_item_state(core_state_name, 0)
        high_load_duration = this_time - timestamp
        state, infotext, _ = check_levels(
            high_load_duration,
            "%s_is_under_high_load_for" % core,  # Not used
            (warn_core, crit_core),
            human_readable_func=get_age_human_readable,
            infoname="%s is under high load for" % core,
        )
        if timestamp == 0:
            set_item_state(core_state_name, this_time)
        elif state:
            return state, infotext, []
        return 0, "", []

    clear_item_state(core_state_name)
    return 0, "", []
