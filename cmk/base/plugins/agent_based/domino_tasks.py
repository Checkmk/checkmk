#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Dict, List, Optional, Tuple

from .agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    Parameters,
    SNMPStringTable,
)

from .utils import ps, domino
from .agent_based_api.v1 import register, SNMPTree

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

ProcessLines = List[Tuple[Optional[str], ps.ps_info, List[str]]]


# Bring the SNMP data in the format expected by the common ps functions.
# e.g.:
# [None, (u'root', u'185292', u'5804', u'00:00:02/03:33:13', u'1'), u'/sbin/init', u'splash']
def parse_domino_tasks(string_table: SNMPStringTable) -> ps.Section:
    process_lines = [(ps.ps_info(), line) for line in string_table[0]]  # type: ignore[call-arg]
    # add cpu_cores count to be compatible with ps section
    return 1, process_lines


register.snmp_section(
    name='domino_tasks',
    parse_function=parse_domino_tasks,
    trees=[
        SNMPTree(
            base=".1.3.6.1.4.1.334.72.1.1.6.1.2.1",
            oids=["4"],  # InTaskName
        ),
    ],
    detect=domino.DETECT,
)


def discover_domino_tasks(
    params: List[Parameters],
    section_domino_tasks: Optional[ps.Section],
    section_mem: Optional[Dict[str, float]],
) -> DiscoveryResult:
    yield from ps.discover_ps(params, section_domino_tasks, section_mem, None)


def check_domino_tasks(
    item: str,
    params: Parameters,
    section_domino_tasks: Optional[ps.Section],
    section_mem: Optional[Dict[str, float]],
) -> CheckResult:
    if section_domino_tasks is None:
        return
    cpu_cores, lines = section_domino_tasks
    process_lines: ProcessLines = [(None, psi, cmd_line) for (psi, cmd_line) in lines]

    yield from ps.check_ps_common(
        label="Tasks",
        item=item,
        params=params,
        process_lines=process_lines,
        total_ram=section_mem.get("MemTotal") if section_mem else None,
        cpu_cores=cpu_cores,
    )


def cluster_check_domino_tasks(
    item: str,
    params: Parameters,
    section_domino_tasks: Dict[str, ps.Section],
    section_mem: Dict[str, Dict[str, int]],
) -> CheckResult:

    process_lines: ProcessLines = [(node_name, psi, cmd_line)
                                   for node_name, node_section in section_domino_tasks.items()
                                   for (psi, cmd_line) in node_section[1]]

    yield from ps.check_ps_common(
        label="Tasks",
        item=item,
        params=params,
        process_lines=process_lines,
        total_ram=None,
        cpu_cores=1,
    )


register.check_plugin(
    name='domino_tasks',
    service_name="Domino Task %s",
    sections=["domino_tasks", "mem"],
    discovery_function=discover_domino_tasks,
    discovery_ruleset_name="inv_domino_tasks_rules",
    discovery_ruleset_type="all",
    discovery_default_parameters={},
    check_function=check_domino_tasks,
    check_ruleset_name="domino_tasks",
    check_default_parameters={},
    cluster_check_function=cluster_check_domino_tasks,
)
