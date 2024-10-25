#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#

import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)


@dataclass(frozen=True)
class Queue:
    name: str
    messages: int


Section = Mapping[str, Sequence[Queue]]


def _process_line(line: str) -> Iterator[tuple[str, Queue]]:
    # Split the line into site name and JSON data
    token: list[str] = line.split(" ", 1)

    # Return early if the line does not contain both site name and data
    if len(token) < 2:
        return

    site_name, data = token
    json_data = json.loads(data)

    for entry in json_data:
        name = entry["name"].split(".")
        messages = int(entry["messages"])
        # ignoring other queues such intersite queue
        if name[1] == "app":
            item = f"{site_name} {name[2]}"
            yield item, Queue(name=name[3], messages=messages)


def _aggregate_queues(queues: Sequence[tuple[str, Queue]]) -> Section:
    result: dict = {}
    for key, queue in queues:
        result.setdefault(key, []).append(queue)
    return result


def parse(string_table: StringTable) -> Section:
    return _aggregate_queues([item for (word,) in string_table for item in _process_line(word)])


agent_section_omd_broker_queues = AgentSection(
    name="omd_broker_queues",
    parse_function=parse,
)


def discovery(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check(item: str, section: Section) -> CheckResult:
    if (queues := section.get(item)) is None:
        return

    for queue in queues:
        yield Result(state=State.OK, summary=f"Messages in queue '{queue.name}': {queue.messages}")


check_plugin_omd_broker_queues = CheckPlugin(
    name="omd_broker_queues",
    service_name="OMD %s",
    discovery_function=discovery,
    check_function=check,
)
