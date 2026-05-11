#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import time
from collections.abc import Mapping
from typing import Any, Final

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    get_rate,
    get_value_store,
    NoLevelsT,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.cpu_util import check_cpu_util_unix, CPUInfo

SectionDict = dict[
    str,
    (list[tuple[str, int]] | list[tuple[str, list[str]]]),
]

Section = tuple[int | None, SectionDict]


KERNEL_COUNTER_NAMES: Final[dict[str, str]] = {  # order determines the service output!
    "processes": "Process Creations",
    "ctxt": "Context Switches",
    "pgmajfault": "Major Page Faults",
    "pswpin": "Page Swap in",
    "pswpout": "Page Swap Out",
}

_KERNEL_METRICS_NAMES = {
    "ctxt": "context_switches",
    "processes": "process_creations",
    "pgmajfault": "major_page_faults",
    "pswpin": "page_swap_in",
    "pswpout": "page_swap_out",
}


def parse_kernel(string_table: StringTable) -> Section:
    """
    >>> from pprint import pprint
    >>> pprint(parse_kernel([
    ...     ['11238'],
    ...     ['nr_free_pages', '198749'],
    ...     ['pgpgin', '169984814'],
    ...     ['pgpgout', '97137765'],
    ...     ['pswpin', '250829'],
    ...     ['pswpout', '751706'],
    ...     ['pgmajfault', '1795031'],
    ...     ['cpu', '13008772', '12250', '5234590', '181918601',
    ...      '73242', '0', '524563', '0', '0', '0'],
    ... ])[1])
    {'Cpu Utilization': [('cpu',
                          ['13008772',
                           '12250',
                           '5234590',
                           '181918601',
                           '73242',
                           '0',
                           '524563',
                           '0',
                           '0',
                           '0'])],
     'Major Page Faults': [('pgmajfault', 1795031)],
     'Page Swap Out': [('pswpout', 751706)],
     'Page Swap in': [('pswpin', 250829)]}

    """
    try:
        timestamp: int | None = int(string_table[0][0])
    except (IndexError, ValueError):
        timestamp = None

    parsed: dict[str, list] = {}
    for line in string_table[1:]:
        if line[0] in KERNEL_COUNTER_NAMES:
            try:
                parsed.setdefault(KERNEL_COUNTER_NAMES[line[0]], []).append((line[0], int(line[1])))
            except (IndexError, ValueError):
                continue

        if line[0].startswith("cpu"):
            try:
                parsed.setdefault("Cpu Utilization", []).append((line[0], line[1:]))
            except (IndexError, ValueError):
                continue
    return timestamp, parsed


agent_section_kernel = AgentSection(
    name="kernel",
    parse_function=parse_kernel,
    supersedes=["hr_cpu"],
)


def discover_kernel_util(section: Section) -> DiscoveryResult:
    if section[1].get("Cpu Utilization"):
        yield Service()


# Columns of cpu usage /proc/stat:
# - cpuX: number of CPU or only 'cpu' for aggregation
# - user: normal processes executing in user mode
# - nice: niced processes executing in user mode
# - system: processes executing in kernel mode
# - idle: twiddling thumbs
# - iowait: waiting for I/O to complete
# - irq: servicing interrupts
# - softirq: servicing softirqs
# - steal: Stolen time, which is the time spent in other operating systems
#          when running in a virtualized environment (since Linux 2.6.11)
# - guest: Time spent running a virtual CPU for guest operating systems (since Linux 2.6.24)
# - guest_nice: Time spent running a niced guest (since Linux 2.6.33)


def check_kernel_util(params: Mapping[str, Any], section: Section) -> CheckResult:
    total: CPUInfo | None = None
    cores = []

    # Look for entry matching "cpu" (this is the combined load of all cores)
    for cpu in section[1].get("Cpu Utilization", []):
        if cpu[0] == "cpu":
            total = CPUInfo(cpu[0], *cpu[1])  # type: ignore[misc]
        elif cpu[0].startswith("cpu"):
            cores.append(CPUInfo(cpu[0], *cpu[1]))  # type: ignore[misc]

    if total is None:
        yield Result(
            state=State.UNKNOWN,
            summary="Inconsistent data: No line with CPU info found.",
        )
        return

    # total contains now the following columns:
    # 'cpu' user nice system idle wait hw-int sw-int (steal ...)
    # convert number to int
    yield from check_cpu_util_unix(
        cpu_info=total,
        params=params,
        this_time=time.time(),
        value_store=get_value_store(),
        cores=cores,
        values_counter=True,
    )


check_plugin_kernel_util = CheckPlugin(
    name="kernel_util",
    service_name="CPU utilization",
    sections=["kernel"],
    discovery_function=discover_kernel_util,
    check_function=check_kernel_util,
    check_default_parameters={},
    check_ruleset_name="cpu_iowait",
)


def _fixed_or_no_levels(
    levels: tuple[float | None, float | None] | None,
) -> NoLevelsT | FixedLevelsT[float]:
    if levels is None or levels[0] is None or levels[1] is None:
        return ("no_levels", None)
    return ("fixed", (levels[0], levels[1]))


def discover_kernel_performance(section: Section) -> DiscoveryResult:
    _, items = section
    for name in KERNEL_COUNTER_NAMES.values():
        if items.get(name):
            yield Service()
            return


def check_kernel_performance(params: Mapping[str, Any], section: Section) -> CheckResult:
    timestamp, items = section
    if timestamp is None:
        return

    for item_name in KERNEL_COUNTER_NAMES.values():
        item_values = items.get(item_name)
        if item_values is None:
            continue

        if len(item_values) > 1:
            yield Result(
                state=State.UNKNOWN,
                summary=f"item {item_name!r} not unique (found {len(item_values)} times)",
            )

        counter, value = item_values[0]
        if not isinstance(value, int):
            continue
        rate = get_rate(get_value_store(), counter, timestamp, value, raise_overflow=True)
        metric_name = _KERNEL_METRICS_NAMES[counter]

        if counter in ("pswpin", "pswpout"):
            yield from check_levels(
                rate,
                metric_name=metric_name,
                levels_upper=_fixed_or_no_levels(params.get(f"{metric_name}_levels")),
                levels_lower=_fixed_or_no_levels(params.get(f"{metric_name}_levels_lower")),
                render_func=lambda x: f"{x:.2f}/s",
                label=item_name,
                boundaries=(0, None),
            )
        else:
            yield from check_levels(
                rate,
                metric_name=metric_name,
                levels_upper=_fixed_or_no_levels(params.get(counter)),
                render_func=lambda x: f"{x:.2f}/s",
                label=item_name,
                boundaries=(0, None),
            )


check_plugin_kernel_performance = CheckPlugin(
    name="kernel_performance",
    service_name="Kernel Performance",
    sections=["kernel"],
    discovery_function=discover_kernel_performance,
    check_function=check_kernel_performance,
    check_ruleset_name="kernel_performance",
    check_default_parameters={},
)
