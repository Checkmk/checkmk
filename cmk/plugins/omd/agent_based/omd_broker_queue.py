#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#

import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Final

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

from .libbroker import node_to_site, Queue, SectionQueues

# These could still be enforced, but don't autodiscover them
_ENFORCED_ONLY_APPS: Final = ("cmk-broker-test",)
DEFAULT_VHOST_NAME: Final = "/"


def parse(string_table: StringTable) -> SectionQueues:
    parsed: dict[str, list[Queue]] = defaultdict(list)

    for (word,) in string_table:
        for raw_queue in json.loads(word):
            parsed[node_to_site(raw_queue["node"])].append(
                Queue(
                    vhost=str(raw_queue["vhost"]),
                    name=raw_queue["name"],
                    messages=int(raw_queue["messages"]),
                )
            )

    return parsed


agent_section_omd_broker_queues = AgentSection(
    name="omd_broker_queues",
    parse_function=parse,
)


def _site_application(section: SectionQueues) -> Mapping[tuple[str, str], Sequence[Queue]]:
    site_application: dict = {}
    for site, queues in section.items():
        for queue in queues:
            queue_name = queue.name.split(".")
            # ignoring other queues such intersite queue
            if queue.vhost != DEFAULT_VHOST_NAME or queue_name[1] != "app":
                continue
            site_application.setdefault((site, queue_name[2]), []).append(queue)

    return site_application


def discover_omd_broker_queues(section: SectionQueues) -> DiscoveryResult:
    yield from (
        Service(item=f"{site} {application}")
        for site, application in _site_application(section)
        if application not in _ENFORCED_ONLY_APPS
    )


def check(item: str, section: SectionQueues) -> CheckResult:
    site, application = item.split(maxsplit=1)
    if (queues := _site_application(section).get((site, application))) is None:
        return

    yield from check_levels(
        sum(q.messages for q in queues),
        metric_name="messages",
        label="Queued messages",
        render_func=str,
    )
    for queue in queues:
        yield Result(
            state=State.OK,
            summary=f"Messages in queue '{queue.name.split('.')[-1]}': {queue.messages}",
        )


check_plugin_omd_broker_queues = CheckPlugin(
    name="omd_broker_queues",
    service_name="OMD %s",
    discovery_function=discover_omd_broker_queues,
    check_function=check,
)
