#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, List, Mapping, MutableMapping, NamedTuple, Optional, Tuple

from ..agent_based_api.v1 import (
    check_levels,
    check_levels_predictive,
    get_average,
    IgnoreResultsError,
    Metric,
    regex,
    render,
)
from ..agent_based_api.v1.type_defs import CheckResult


class CPUInfo(
    NamedTuple(  # pylint: disable=typing-namedtuple-call
        "_CPUInfo",
        [
            ("name", str),
            ("user", float),
            ("nice", float),
            ("system", float),
            ("idle", float),
            ("iowait", float),
            ("irq", float),
            ("softirq", float),
            ("steal", float),
            ("guest", float),
            ("guest_nice", float),
        ],
    )
):
    """Handle CPU measurements

    name: name of core
    user: normal processes executing in user mode
    nice: niced processes executing in user mode
    system: processes executing in kernel mode
    idle: twiddling thumbs
    iowait: waiting for I/O to complete
    irq: servicing interrupts
    softirq: servicing softirqs
    steal: involuntary wait
    guest: time spent in guest OK, also counted in 0 (user)
    guest_nice: time spent in niced guest OK, also counted in 1 (nice)
    """

    def __new__(cls, name: str, *values: float) -> "CPUInfo":
        # we can assume we have at least one value
        caster = int if values and isinstance(values[0], int) else float
        fillup = (caster(0) for _ in range(10 - len(values)))
        return super().__new__(cls, name, *(caster(v) for v in values), *fillup)

    @property
    def util_total(self) -> float:
        return (
            self.user + self.nice + self.system + self.iowait + self.irq + self.softirq + self.steal
        )

    @property
    def total_sum(self) -> float:
        return self.util_total + self.idle

    @property
    def utils_perc(self) -> Tuple[float, float, float, float, float, float]:
        # https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/tree/kernel/sched/cputim  e.c
        # see 'account_guest_time'
        # if task_nice(p) <= 0:
        #     cpustat[CPUTIME_USER] += cputime;
        #     cpustat[CPUTIME_GUEST] += cputime;
        guest = self.guest + self.guest_nice
        user = self.user + self.nice - guest
        system = self.system + self.irq + self.softirq

        total_sum = self.total_sum

        def _percent(x: float) -> float:
            return 100.0 * float(x) / float(total_sum)

        return (
            _percent(user),
            _percent(system),
            _percent(self.iowait),
            _percent(self.steal),
            _percent(guest),
            _percent(self.util_total),
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
    *,
    util: float,
    params: Mapping[str, Any],
    cores: Optional[List[Tuple[str, float]]] = None,
    perf_max: Optional[float] = 100,
    value_store: MutableMapping[str, Any],
    this_time: float,
) -> CheckResult:
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

    # Averaging
    if "average" in params:
        yield Metric(
            "util",
            util,
            levels=levels if isinstance(levels, tuple) else None,  # type: ignore[arg-type]
            boundaries=(0, perf_max),
        )
        value_checked = get_average(
            value_store,
            "cpu_utilization.avg",
            this_time,
            util,
            params["average"],
        )
        metric_name = "util_average"
        label = "Total CPU (%d min average)" % params["average"]
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
        boundaries=(0, None),
    ) if isinstance(levels, dict) else check_levels(
        value_checked,
        metric_name=metric_name,
        levels_upper=levels,
        render_func=render.percent,
        label=label,
        boundaries=(0, None),
    )

    if "core_util_time_total" in params:
        threshold, warn, crit = params["core_util_time_total"]
        yield from cpu_util_time(
            core="total",
            perc=util,
            threshold=threshold,
            levels=(warn, crit),
            value_store=value_store,
            this_time=this_time,
        )

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
            yield from _util_perfdata(
                core=core,
                core_index=core_index,
                total_perc=total_perc,
                params=params,
                value_store=value_store,
                this_time=this_time,
            )


def check_cpu_util_unix(
    *,
    cpu_info: CPUInfo,
    params: Mapping,
    this_time: float,
    value_store: MutableMapping,
    cores: List[CPUInfo],
    values_counter: bool,
) -> CheckResult:
    if values_counter:
        diff_values = _util_counter(cpu_info, value_store)
        sum_jiffies = diff_values.total_sum
        if sum_jiffies == 0:
            raise IgnoreResultsError("Too short time difference since last check")
        (
            user_perc,
            system_perc,
            wait_perc,
            steal_perc,
            guest_perc,
            util_total_perc,
        ) = diff_values.utils_perc
    else:
        user_perc = cpu_info.user
        system_perc = cpu_info.system
        wait_perc = cpu_info.iowait
        steal_perc = cpu_info.steal
        guest_perc = cpu_info.guest
        util_total_perc = cpu_info.util_total

    yield from check_levels(
        user_perc,
        metric_name="user",
        render_func=render.percent,
        label="User",
        notice_only=True,
    )
    yield from check_levels(
        system_perc,
        metric_name="system",
        render_func=render.percent,
        label="System",
        notice_only=True,
    )
    yield from check_levels(
        wait_perc,
        metric_name="wait",
        levels_upper=params.get("iowait"),
        render_func=render.percent,
        label="Wait",
        notice_only=True,
    )

    # Compute values used in virtualized environments (Xen, etc.)
    # Only do this for counters that have counted at least one tick
    # since the system boot. This avoids silly output in systems
    # where these counters are not being used
    if cpu_info.steal:
        yield from check_levels(
            steal_perc,
            metric_name="steal",
            levels_upper=params.get("steal"),
            render_func=render.percent,
            label="Steal",
            notice_only=True,
        )

    if cpu_info.guest:
        yield from check_levels(
            guest_perc,
            metric_name="guest",
            render_func=render.percent,
            label="Guest",
            notice_only=True,
        )

    summary_cores = []
    for core in cores:
        key = f"cpu.util.{core.name}.total"
        prev_total = value_store.get(key, 0)
        util_total = core.util_total
        total_diff = util_total - prev_total
        value_store[key] = util_total
        total_perc = (100.0 * total_diff / sum_jiffies) * len(cores)
        summary_cores.append((core.name, total_perc))

    yield from check_cpu_util(
        value_store=value_store,
        util=util_total_perc,
        params=params,
        this_time=this_time,
        cores=summary_cores,
        perf_max=None,
    )


def _check_single_core_util(
    util: float,
    metric: Optional[str],
    levels: Optional[Tuple[float, float]],
    label: str,
) -> CheckResult:
    yield from check_levels(
        util,
        levels_upper=levels,
        render_func=render.percent,
        label=label,
        metric_name=metric,
        notice_only=True,
    )


def _util_perfdata(
    *,
    core: str,
    core_index: int,
    total_perc: float,
    params: Mapping,
    value_store: MutableMapping[str, Any],
    this_time: float,
) -> CheckResult:
    """Check a single cores performance.

    Only sends `notice` output.
    """
    if "core_util_time" in params:
        threshold, warn, crit = params["core_util_time"]
        yield from cpu_util_time(
            core=core,
            perc=total_perc,
            threshold=threshold,
            levels=(warn, crit),
            value_store=value_store,
            this_time=this_time,
        )

    config_single_avg = params.get("average_single", {})

    metric_names: Tuple[Optional[str], Optional[str]] = core_name(core, core_index)
    metric_raw, metric_avg = metric_names
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
    *,
    core: str,
    perc: float,
    threshold: float,
    levels: Optional[Tuple[float, float]],
    value_store: MutableMapping[str, Any],
    this_time: float,
) -> CheckResult:
    """Check for how long a CPU was under high load.

    Only sends `notice` output .
    """
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
        notice_only=True,
    )


def _util_counter(
    stats: CPUInfo,
    value_store: MutableMapping[str, Any],
) -> CPUInfo:
    """Compute jiffi-differences of all relevant counters"""
    diff_values = []
    for field, value in zip(stats._fields[1:], stats[1:]):
        key = f"cpu.util.{field}"
        diff_values.append(value - value_store.get(key, 0))
        value_store[key] = value

    return CPUInfo(stats.name, *diff_values)
