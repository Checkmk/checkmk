#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, timedelta
from typing import Dict, Final, List, NamedTuple

from .agent_based_api.v1 import register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import sap_hana


class InstanceProcess(NamedTuple):
    name: str
    state: str
    description: str
    elapsed_time: float
    pid: str


class InstanceStatus(NamedTuple):
    status: str
    processes: List[InstanceProcess] = []


INSTANCE_STATUSES: Final = {
    "0": "Error getting processes",
    "1": "Error getting processes",
    "2": "Timeout",
    "3": "OK",
    "4": "All processes stopped",
}


def _parse_elapsed_time(time_string):
    try:
        time = datetime.strptime(time_string, "%H:%M:%S")
    except ValueError:
        return None

    elapsed_time = timedelta(hours=time.hour, minutes=time.minute, seconds=time.second)
    return elapsed_time.total_seconds()


def parse_sap_hana_instance_status(string_table: StringTable) -> Dict[str, InstanceStatus]:
    section: Dict[str, InstanceStatus] = {}

    for sid_instance, lines in sap_hana.parse_sap_hana(string_table).items():
        status = lines[0][0].split(":")[1].lstrip()
        if INSTANCE_STATUSES.get(status) != "OK":
            section[sid_instance] = InstanceStatus(status=status)
            continue

        processes = [
            InstanceProcess(
                name=line[1],
                state=line[2],
                description=line[3],
                elapsed_time=_parse_elapsed_time(line[5]),
                pid=line[6],
            )
            for line in lines[3:]
        ]

        section[sid_instance] = InstanceStatus(status=status, processes=processes)

    return section


register.agent_section(
    name="sap_hana_instance_status",
    parse_function=parse_sap_hana_instance_status,
)


def discovery_sap_hana_instance_status(section: Dict[str, InstanceStatus]) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_sap_hana_instance_status(item: str, section: Dict[str, InstanceStatus]) -> CheckResult:
    instance = section.get(item)
    if instance is None:
        return

    status_description = INSTANCE_STATUSES.get(instance.status, "Error getting processes")
    if status_description != "OK":
        yield Result(state=State.CRIT, summary=status_description)
        return

    yield Result(state=State.OK, summary=status_description)

    for p in instance.processes:
        state = State.OK if p.state == "GREEN" else State.WARN
        timespan = f"for {render.timespan(p.elapsed_time)}" if p.elapsed_time else ""
        process_summary = f"{p.name}: {p.description} {timespan}, PID: {p.pid}"
        yield Result(state=state, summary=process_summary)


register.check_plugin(
    name="sap_hana_instance_status",
    service_name="SAP HANA Instance Status %s",
    discovery_function=discovery_sap_hana_instance_status,
    check_function=check_sap_hana_instance_status,
)
