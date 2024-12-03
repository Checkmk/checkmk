#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#

import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

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

# These could still be enforced, but don't autodiscover them
_ENFORCED_ONLY_APPS: Final = ("cmk-broker-test",)
DEFAULT_VHOST_NAME: Final = "/"


@dataclass(frozen=True)
class Queue:
    vhost: str
    name: str
    messages: int


Section = Mapping[str, Sequence[Queue]]


def parse(string_table: StringTable) -> Section:
    parsed: dict[str, list[Queue]] = defaultdict(list)
    for line in string_table:
        try:
            site, vhost, queues_line = line[0].split(" ", 2)
        except ValueError:
            continue

        queues_json = json.loads(queues_line)
        parsed[site].extend(
            Queue(vhost=vhost, name=queue["name"], messages=queue["messages"])
            for queue in queues_json
        )

    return parsed


agent_section_omd_broker_queues = AgentSection(
    name="omd_broker_queues",
    parse_function=parse,
)


def _site_application(section: Section) -> Mapping[tuple[str, str], Sequence[Queue]]:
    site_application: dict = {}
    for site, queues in section.items():
        for queue in queues:
            queue_name = queue.name.split(".")
            # ignoring other queues such intersite queue
            if queue.vhost != DEFAULT_VHOST_NAME or queue_name[1] != "app":
                continue
            site_application.setdefault((site, queue_name[2]), []).append(queue)

    return site_application


def discover_omd_broker_queues(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=f"{site} {application}")
        for site, application in _site_application(section)
        if application not in _ENFORCED_ONLY_APPS
    )


def check(item: str, section: Section) -> CheckResult:
    site, application = item.split(maxsplit=1)
    if (queues := _site_application(section).get((site, application))) is None:
        return

    for queue in queues:
        yield Result(
            state=State.OK,
            summary=f"Messages in queue '{queue.name.split(".")[-1]}': {queue.messages}",
        )


check_plugin_omd_broker_queues = CheckPlugin(
    name="omd_broker_queues",
    service_name="OMD %s",
    discovery_function=discover_omd_broker_queues,
    check_function=check,
)
