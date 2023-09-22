#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package

import dataclasses
from collections.abc import Mapping

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


@dataclasses.dataclass
class Section:
    instance_to_pid: Mapping[str, int | None]
    all_pids: frozenset[int]


def parse_postgres_instances(string_table: StringTable) -> Section:
    instance_to_pid: dict[str, int | None] = {}
    all_pids = []
    is_single = False
    for line in string_table:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            instance_name = line[0][3:-3].upper()
            is_single = True
            instance_to_pid.setdefault(instance_name, None)
        elif len(line) >= 4:
            if not is_single:
                instance_name = line[3].split("/")[-1].upper()
                instance_to_pid.setdefault(instance_name, None)
            try:
                pid = int(line[0])
                all_pids.append(pid)
                instance_to_pid[instance_name] = pid
            except ValueError:
                pass
    instance_to_pid.pop("", None)

    return Section(instance_to_pid=instance_to_pid, all_pids=frozenset(all_pids))


register.agent_section(
    name="postgres_instances",
    parse_function=parse_postgres_instances,
)


def discover_postgres_instances(section: Section) -> DiscoveryResult:
    yield from (Service(item=name) for name in section.instance_to_pid)


def check_postgres_instances(item: str, section: Section) -> CheckResult:
    if (pid := section.instance_to_pid.get(item)) is not None:
        yield Result(state=State.OK, summary=f"Status: running with PID {pid}")
    else:
        yield Result(
            state=State.CRIT,
            summary=(
                f"Instance {item} not running or postgres DATADIR name is not identical with "
                "instance name."
            ),
        )


register.check_plugin(
    name="postgres_instances",
    service_name="PostgreSQL Instance %s",
    discovery_function=discover_postgres_instances,
    check_function=check_postgres_instances,
)


def discover_postgres_processes(section: Section) -> DiscoveryResult:
    yield Service()


def check_postgres_processes(section: Section) -> CheckResult:
    count = len(section.all_pids)
    if count == 0:
        yield Result(state=State.CRIT, summary=str(count), details="No process matched")
        return
    yield Result(state=State.OK, summary=str(count), details="PIDs")
    for pid in section.all_pids:
        yield Result(state=State.OK, notice=str(pid))


register.check_plugin(
    name="postgres_processes",
    sections=["postgres_instances"],
    service_name="PostgreSQL Process Count",
    discovery_function=discover_postgres_processes,
    check_function=check_postgres_processes,
)
