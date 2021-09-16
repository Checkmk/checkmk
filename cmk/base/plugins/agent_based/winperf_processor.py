#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Final, List, Mapping, MutableMapping, NamedTuple, Optional, Tuple

from .agent_based_api.v1 import (
    check_levels,
    get_rate,
    get_value_store,
    IgnoreResults,
    IgnoreResultsError,
    Metric,
    register,
    render,
    Result,
    Service,
    State,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.cpu_util import check_cpu_util


class CoreTicks(NamedTuple):
    name: str
    total: int
    per_core: List[int]


class Section(NamedTuple):
    time: int
    ticks: List[CoreTicks]


WHAT_MAP: Final = {"-232": "util", "-96": "user", "-94": "privileged"}


def parse_winperf_processor(string_table: StringTable) -> Optional[Section]:
    section = Section(
        time=int(float(string_table[0][0])),
        ticks=[],
    )
    for line in string_table[1:]:
        what = WHAT_MAP.get(line[0])
        if what is None:
            continue
        # behaviour of raising ValueError kept during migration
        section.ticks.append(
            CoreTicks(name=what, total=int(line[-2]), per_core=[int(t) for t in line[1:-2]])
        )

    return section


register.agent_section(
    name="winperf_processor",
    parse_function=parse_winperf_processor,
    supersedes=["hr_cpu"],
)


def discover_winperf_processor_util(section: Section) -> DiscoveryResult:
    if section.ticks:
        yield Service()


def _clamp_percentage(value: float) -> float:
    """clamp percentage to the range 0-100

    Due to timing invariancies the measured level can become > 100%.
    This makes users unhappy, so cut it off.
    """
    return min(100.0, max(0.0, value))


def _ticks_to_percent(
    value_store: MutableMapping[str, Any],
    ticks: CoreTicks,
    this_time: float,
    index: Optional[int] = None,
) -> float:
    """Convert ticks (100ns) to a number between 0 and 100"""
    value = ticks.total if index is None else ticks.per_core[index]
    key = f"{ticks.name}" if index is None else f"{ticks.name}.{index}"
    ticks_per_sec = get_rate(value_store, key, this_time, value, raise_overflow=True)

    # 1 tick = 100ns, convert to seconds (*1e-7) and to percent (*1e2)
    percentage = _clamp_percentage(ticks_per_sec * 1e-5)

    # if name == "util"
    # We get the value of the PERF_100NSEC_TIMER_INV.
    # This counter type shows the average percentage of active time observed
    # during the sample interval. This is an inverse counter. Counters of this
    # type calculate active time by measuring the time that the service was
    # inactive and then subtracting the percentage of active time from 100 percent.
    return 100.0 - percentage if ticks.name == "util" else percentage


def _simple_ok_result(
    value_store: MutableMapping[str, Any],
    ticks: CoreTicks,
    this_time: float,
) -> CheckResult:
    try:
        yield from check_levels(
            _ticks_to_percent(value_store, ticks, this_time),
            metric_name=ticks.name,
            render_func=render.percent,
            label=ticks.name.capitalize(),
            notice_only=True,
        )
    except IgnoreResultsError as exc:
        yield IgnoreResults(f"{exc}")


def _get_cores(
    value_store: MutableMapping[str, Any],
    ticks: CoreTicks,
    this_time: float,
) -> List[Tuple[str, float]]:
    cores = []
    for idx in range(len(ticks.per_core)):
        try:
            cores.append(
                (
                    "core%d" % idx,
                    _ticks_to_percent(value_store, ticks, this_time, idx),
                )
            )
        except IgnoreResultsError:
            continue
    return cores


def _encode_cpu_count_in_boundary(generator: CheckResult, num_cpus: int) -> CheckResult:
    for res in generator:
        if isinstance(res, Metric) and res.name == "util":
            yield Metric(
                res.name, res.value, levels=res.levels, boundaries=(res.boundaries[0], num_cpus)
            )
            break
        yield res
    yield from generator


def check_winperf_processor_util(params: Mapping[str, Any], section: Section) -> CheckResult:
    if not section.ticks:
        return

    num_cpus = len(section.ticks[0].per_core)
    value_store = get_value_store()

    for ticks in section.ticks:

        if ticks.name != "util":
            yield from _simple_ok_result(value_store, ticks, section.time)
            continue

        cores = _get_cores(value_store, ticks, section.time)
        try:
            used_perc = _ticks_to_percent(value_store, ticks, section.time)
        except IgnoreResultsError as exc:
            yield IgnoreResults(f"{exc}")
            continue

        yield from _encode_cpu_count_in_boundary(
            check_cpu_util(
                util=used_perc,
                params=params,
                cores=cores,
                value_store=value_store,
                this_time=section.time,
            ),
            num_cpus,
        )

    yield Result(state=State.OK, notice=f"Number of processors: {num_cpus}")
    yield Metric("cpus", num_cpus)  # seriously?


register.check_plugin(
    name="winperf_processor_util",
    service_name="CPU utilization",
    sections=["winperf_processor"],
    discovery_function=discover_winperf_processor_util,
    check_function=check_winperf_processor_util,
    check_default_parameters={},
    check_ruleset_name="cpu_utilization_os",
)
