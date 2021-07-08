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

from .agent_based_api.v1 import register, Service, State, Result


def discover_kaspersky_av_tasks(section):
    jobs = ['Real-time protection', 'System:EventManager']
    for line in [x for x in section if x[0].startswith("Name")]:
        job = " ".join(line[1:])
        if job in jobs:
            yield Service(item=job)


def check_kaspersky_av_tasks(item, section):
    found = False
    for line in section:
        if found:
            if line[0].startswith('State'):
                state = State.OK
                if line[1] != "Started":
                    state = State.CRIT
                yield Result(state=state, summary="Current state is " + line[1])
                return
        if line[0].startswith('Name') and " ".join(line[1:]) == item:
            found = True
    yield Result(state=State.UNKNOWN, summary="Task not found in agent output")


register.check_plugin(
    name="kaspersky_av_tasks",
    service_name="AV Task %s",
    discovery_function=discover_kaspersky_av_tasks,
    check_function=check_kaspersky_av_tasks,
)
