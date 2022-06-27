#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .agent_based_api.v1 import register, SNMPTree
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import domino, memory, ps

# Example SNMP walk:
#
# InTaskName: The actual name of the task as it appears in the SERVER.TASK statistic on the server.
# .1.3.6.1.4.1.334.72.1.1.6.1.2.1.4.0 Router
# .1.3.6.1.4.1.334.72.1.1.6.1.2.1.4.1 tm_grab Subsystems
# .1.3.6.1.4.1.334.72.1.1.6.1.2.1.4.2 tm_grab M01
# .1.3.6.1.4.1.334.72.1.1.6.1.2.1.4.3 tm_grab M02
# .1.3.6.1.4.1.334.72.1.1.6.1.2.1.4.4 tm_grab M03
# .1.3.6.1.4.1.334.72.1.1.6.1.2.1.4.5 tm_grab M04
# .1.3.6.1.4.1.334.72.1.1.6.1.2.1.4.6 tm_grab M05
# .1.3.6.1.4.1.334.72.1.1.6.1.2.1.4.7 tm_grab
# .1.3.6.1.4.1.334.72.1.1.6.1.2.1.4.8 Router

# Bring the SNMP data in the format expected by the common ps functions.
# e.g.:
# [PsInfo(), u'/sbin/init', u'splash']
def parse_domino_tasks(string_table: List[StringTable]) -> ps.Section:
    process_lines = [(ps.PsInfo(), line) for line in string_table[0]]
    # add cpu_cores count to be compatible with ps section
    return 1, process_lines


register.snmp_section(
    name="domino_tasks",
    parse_function=parse_domino_tasks,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.334.72.1.1.6.1.2.1",
            oids=["4"],  # InTaskName
        ),
    ],
    detect=domino.DETECT,
)


def discover_domino_tasks(
    params: Sequence[Mapping[str, Any]],
    section_domino_tasks: Optional[ps.Section],
    section_mem: Optional[memory.SectionMem],
) -> DiscoveryResult:
    yield from ps.discover_ps(params, section_domino_tasks, section_mem, None, None)


def check_domino_tasks(
    item: str,
    params: Mapping[str, Any],
    section_domino_tasks: Optional[ps.Section],
    section_mem: Optional[Dict[str, float]],
) -> CheckResult:
    if section_domino_tasks is None:
        return
    cpu_cores, lines = section_domino_tasks
    process_lines = [(None, psi, cmd_line) for (psi, cmd_line) in lines]

    total_ram = section_mem.get("MemTotal") if section_mem else None

    yield from ps.check_ps_common(
        label="Tasks",
        item=item,
        params=params,
        process_lines=process_lines,
        total_ram_map={} if total_ram is None else {"": total_ram},
        cpu_cores=cpu_cores,
    )


def cluster_check_domino_tasks(
    item: str,
    params: Mapping[str, Any],
    section_domino_tasks: Mapping[str, Optional[ps.Section]],
    section_mem: Mapping[str, Optional[memory.SectionMem]],
) -> CheckResult:

    iter_non_trivial_sections = (
        (node_name, node_section)
        for node_name, node_section in section_domino_tasks.items()
        if node_section is not None
    )
    process_lines = [
        (node_name, psi, cmd_line)
        for node_name, node_section in iter_non_trivial_sections
        for (psi, cmd_line) in node_section[1]
    ]

    yield from ps.check_ps_common(
        label="Tasks",
        item=item,
        params=params,
        process_lines=process_lines,
        total_ram_map={
            node: section["MemTotal"]
            for node, section in section_mem.items()
            if section and "MemTotal" in section
        },
        cpu_cores=1,
    )


register.check_plugin(
    name="domino_tasks",
    service_name="Domino Task %s",
    sections=["domino_tasks", "mem"],
    discovery_function=discover_domino_tasks,
    discovery_ruleset_name="inv_domino_tasks_rules",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters={},
    check_function=check_domino_tasks,
    # Note: domino_tasks is a ManualCheckParameterRulespec.
    # If the user specifies an already discovered item, the enforced service will shadow the
    # corresponding autocheck. As a result, to the user it looks as if the parameters specified in
    # the enforced service configuration were simply passed to the check plugin, without any sort of
    # shadowing.
    # Also note that we cannot simply remove this line. If we did that, the plugin domino_tasks
    # would not be available any more when configuring enforced services.
    check_ruleset_name="domino_tasks",
    check_default_parameters={},
    cluster_check_function=cluster_check_domino_tasks,
)
