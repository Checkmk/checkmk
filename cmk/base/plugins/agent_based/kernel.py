#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Any, Dict, Final, List, Mapping, Optional, Tuple, Union

from .agent_based_api.v1 import get_value_store, register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.cpu_util import check_cpu_util_unix, CPUInfo

SectionDict = Dict[
    str,
    Union[
        List[Tuple[str, int]],  #
        List[Tuple[str, List[str]]],  # TODO: .util.cpu_util.CPUInfo?
    ],
]

Section = Tuple[Optional[int], SectionDict]


KERNEL_COUNTER_NAMES: Final[Dict[str, str]] = {  # order determines the service output!
    "processes": "Process Creations",
    "ctxt": "Context Switches",
    "pgmajfault": "Major Page Faults",
    "pswpin": "Page Swap in",
    "pswpout": "Page Swap Out",
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
        timestamp: Optional[int] = int(string_table[0][0])
    except (IndexError, ValueError):
        timestamp = None

    parsed: Dict[str, List] = {}
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


register.agent_section(
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
    total: Optional[CPUInfo] = None
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


register.check_plugin(
    name="kernel_util",
    service_name="CPU utilization",
    sections=["kernel"],
    discovery_function=discover_kernel_util,
    check_function=check_kernel_util,
    check_default_parameters={},
    check_ruleset_name="cpu_iowait",
)
