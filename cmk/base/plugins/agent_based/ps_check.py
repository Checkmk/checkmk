#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, List, Optional, Tuple
from .agent_based_api.v1.type_defs import CheckResult, Parameters

from .agent_based_api.v1 import register
from .utils import ps


def check_ps(
    item: str,
    params: Parameters,
    section_ps: ps.Section,
    section_mem: ps.SectionMem,
    section_cpu: ps.SectionCpu,
) -> CheckResult:
    if not section_ps:
        return

    cpu_cores, lines = section_ps
    if section_cpu:
        cpu_cores = section_cpu.get('num_cpus') or cpu_cores  # type: ignore[assignment]

    total_ram = section_mem.get("MemTotal") if section_mem else None

    yield from ps.check_ps_common(
        label="Processes",
        item=item,
        params=params,
        # no cluster in this function -> Node name is None:
        process_lines=[(None, ps_info, cmd_line) for ps_info, cmd_line in lines],
        cpu_cores=cpu_cores,
        total_ram=total_ram,
    )


def cluster_check_ps(
        item: str,
        params: Parameters,
        section_ps: Dict[str, ps.Section],
        section_mem: Dict[str, ps.SectionMem],  # unused
        section_cpu: Dict[str, ps.SectionCpu],  # unused
) -> CheckResult:
    # introduce node name
    process_lines: List[Tuple[Optional[str], ps.ps_info, List[str]]] = [
        (node_name, ps_info, cmd_line)
        for node_name, (_cpu_cores, node_lines) in section_ps.items()
        for (ps_info, cmd_line) in node_lines
    ]

    core_counts = set(cpu_cores for (cpu_cores, _node_lines) in section_ps.values())
    if len(core_counts) == 1:
        cpu_cores = core_counts.pop()
    else:
        # inconsistent cpu counts, what can we do? There's no 'None' option.
        cpu_cores = 1

    yield from ps.check_ps_common(
        label="Processes",
        item=item,
        params=params,
        process_lines=process_lines,
        cpu_cores=cpu_cores,
        total_ram=None,
    )


register.check_plugin(
    name="ps",
    service_name="Process %s",
    sections=["ps", "mem", "cpu"],
    discovery_function=ps.discover_ps,
    discovery_ruleset_name="inventory_processes_rules",
    discovery_default_parameters={},
    discovery_ruleset_type="all",
    check_function=check_ps,
    check_default_parameters={
        "levels": (1, 1, 99999, 99999),
    },
    check_ruleset_name="ps",
    cluster_check_function=cluster_check_ps,
)
