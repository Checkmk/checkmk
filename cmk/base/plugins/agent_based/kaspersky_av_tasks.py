#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# Number of tasks: 15
# Name: System:EventManager
#         Id: 1
#         Runtime ID: 1314160393
#         Class: EventManager
#         State: Started
# Name: System:AVS
#         Id: 2
#         Runtime ID: 1314160398
#         Class: AVS
#         State: Started
# Name: System:Quarantine
#         Id: 3
#         Runtime ID: 1314160399
#         Class: Quarantine
#         State: Started
# Name: System:Statistics
#         Id: 4
#         Runtime ID: 1314160396
#         Class: Statistics
#         State: Started
#

from collections import defaultdict
from typing import Dict

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

Section = Dict[str, Dict[str, str]]


def parse_kaspersky_av_tasks(string_table: StringTable) -> Section:
    """
    >>> parse_kaspersky_av_tasks([
    ...     ["Name:", "Name0"], ["Value:", "Value0"],
    ...     ["Name:", "Name1"], ["Value:", "Value1"]
    ... ])
    {'Name0': {'Value': 'Value0'}, 'Name1': {'Value': 'Value1'}}
    """
    parsed: Section = defaultdict(dict)
    current_name = None
    for line in string_table:
        if line[0] == "Name:":
            current_name = line[1]
        elif current_name is not None:
            parsed[current_name][line[0].strip(":")] = line[1]
    return dict(parsed)


register.agent_section(
    name="kaspersky_av_tasks",
    parse_function=parse_kaspersky_av_tasks,
)


def discover_kaspersky_av_tasks(section: Section) -> DiscoveryResult:
    """
    >>> list(discover_kaspersky_av_tasks({
    ...     "System:EventManager": dict(),
    ...     "Real-time protection": dict(),
    ...     "System:AVS": dict(),
    ... }))
    [Service(item='System:EventManager'), Service(item='Real-time protection')]
    """
    yield from (
        Service(item=item)
        for item in section.keys()
        if item in {"Real-time protection", "System:EventManager"}
    )


def check_kaspersky_av_tasks(item: str, section: Section) -> CheckResult:
    """
    >>> list(check_kaspersky_av_tasks(
    ...     "System:EventManager", {"System:EventManager": {"State": "Started"}}))
    [Result(state=<State.OK: 0>, summary='Current state is Started')]
    """
    if item not in section:
        yield Result(state=State.UNKNOWN, summary="Task not found in agent output")
        return

    state = section[item].get("State")
    yield Result(
        state=State.OK if state == "Started" else State.CRIT, summary=f"Current state is {state}"
    )


register.check_plugin(
    name="kaspersky_av_tasks",
    service_name="AV Task %s",
    discovery_function=discover_kaspersky_av_tasks,
    check_function=check_kaspersky_av_tasks,
)
