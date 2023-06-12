#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Optional

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import CheckResult
from .utils import cpu, memory, ps


def check_ps(
    item: str,
    params: Mapping[str, Any],
    section_ps: Optional[ps.Section],
    section_mem: Optional[memory.SectionMem],
    section_mem_used: Optional[memory.SectionMem],
    section_cpu: Optional[cpu.Section],
) -> CheckResult:
    if not section_ps:
        return

    cpu_cores, lines, ps_time = section_ps
    if section_cpu:
        cpu_cores = section_cpu.num_cpus or cpu_cores

    total_ram = (section_mem or section_mem_used or {}).get("MemTotal")

    yield from ps.check_ps_common(
        label="Processes",
        item=item,
        params=params,
        # no cluster in this function -> Node name is None:
        process_lines=[(None, ps_info, cmd_line, ps_time) for ps_info, cmd_line in lines],
        cpu_cores=cpu_cores,
        total_ram_map={} if total_ram is None else {"": total_ram},
    )


def cluster_check_ps(
    item: str,
    params: Mapping[str, Any],
    section_ps: Mapping[str, Optional[ps.Section]],
    section_mem: Mapping[str, Optional[memory.SectionMem]],
    section_mem_used: Mapping[str, Optional[memory.SectionMem]],
    section_cpu: Mapping[str, Optional[cpu.Section]],  # unused
) -> CheckResult:
    iter_non_trivial_sections = (
        (node_name, node_section)
        for node_name, node_section in section_ps.items()
        if node_section is not None
    )

    # introduce node name
    process_lines = [
        (node_name, ps_info, cmd_line, node_section[2])
        for node_name, node_section in iter_non_trivial_sections
        for (ps_info, cmd_line) in (node_section[1])
    ]

    core_counts = set(
        node_section[0] for node_section in section_ps.values() if node_section is not None
    )
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
        total_ram_map={
            **{
                node: section["MemTotal"]
                for node, section in section_mem.items()
                if section and "MemTotal" in section
            },
            **{
                node: v
                for node, section in section_mem_used.items()
                if section and (v := section.get("MemTotal")) is not None
            },
        },
    )


register.check_plugin(
    name="ps",
    service_name="Process %s",
    sections=["ps", "mem", "mem_used", "cpu"],
    discovery_function=ps.discover_ps,
    discovery_ruleset_name="inventory_processes_rules",
    discovery_default_parameters={},
    discovery_ruleset_type=register.RuleSetType.ALL,
    check_function=check_ps,
    check_default_parameters={
        "levels": (1, 1, 99999, 99999),
    },
    check_ruleset_name="ps",
    cluster_check_function=cluster_check_ps,
)
