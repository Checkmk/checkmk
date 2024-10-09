#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v1 import Result, State
from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
    StringTable,
)


@dataclass(frozen=True)
class BrokerStatus:
    memory: int
    queues: int


@dataclass(frozen=True)
class Shovel:
    name: str
    state: str


SectionStatus = Mapping[str, BrokerStatus]
SectionShovels = Mapping[str, Sequence[Shovel]]


def parse_omd_broker_status(string_table: StringTable) -> SectionStatus:
    parsed = {}
    for line in string_table:
        try:
            site, status_line = line[0].split(" ", 1)
        except ValueError:
            continue

        status = json.loads(status_line)
        broker_status = BrokerStatus(
            memory=int(status["memory"]["total"]["rss"]),
            queues=int(status["totals"]["queue_count"]),
        )
        parsed[site] = broker_status

    return parsed


agent_section_omd_broker_status = AgentSection(
    name="omd_broker_status",
    parse_function=parse_omd_broker_status,
)


def parse_omd_broker_shovels(string_table: StringTable) -> SectionShovels:
    parsed = {}
    for line in string_table:
        try:
            site, shovels_line = line[0].split(" ", 1)
        except ValueError:
            continue

        shovels_json = json.loads(shovels_line)
        parsed[site] = [
            Shovel(name=shovel["name"], state=shovel["state"]) for shovel in shovels_json
        ]

    return parsed


agent_section_omd_broker_shovels = AgentSection(
    name="omd_broker_shovels",
    parse_function=parse_omd_broker_shovels,
)


def discover_omd_broker_status(
    section_omd_broker_status: SectionStatus | None,
    section_omd_broker_shovels: SectionShovels | None,
) -> DiscoveryResult:
    if section_omd_broker_status:
        yield from (Service(item=site) for site in section_omd_broker_status)


def _check_shovels(item: str, section_omd_broker_shovels: SectionShovels) -> CheckResult:
    if (shovels := section_omd_broker_shovels.get(item)) is None:
        return

    states = Counter(shovel.state for shovel in shovels)

    yield Result(state=State.OK, summary=f"Shovels running: {states["running"]}")
    if states["starting"]:
        yield Result(state=State.OK, summary=f"Shovels starting: {states["starting"]}")
    if states["terminated"]:
        yield Result(state=State.WARN, summary=f"Shovels terminated: {states["terminated"]}")


def check_omd_broker_status(
    item: str,
    section_omd_broker_status: SectionStatus | None,
    section_omd_broker_shovels: SectionShovels | None,
) -> CheckResult:
    if not section_omd_broker_status or (status := section_omd_broker_status.get(item)) is None:
        return

    yield from check_levels(
        status.memory,
        metric_name="mem_used",
        label="Memory",
        render_func=render.bytes,
    )
    yield Result(state=State.OK, summary=f"Queues: {status.queues}")

    if section_omd_broker_shovels:
        yield from _check_shovels(item, section_omd_broker_shovels)


check_plugin_myhostgroups = CheckPlugin(
    name="omd_broker_status",
    sections=["omd_broker_status", "omd_broker_shovels"],
    service_name="OMD %s message broker",
    discovery_function=discover_omd_broker_status,
    check_function=check_omd_broker_status,
)
