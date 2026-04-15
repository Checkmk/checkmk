#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# [[SINGLE_ITEM_EXPORT_int_jens]]
# 0 0 0 0
# [[SPRINGAPP-COMMAND-INBOX-DEV]]
# 0 0 15 15
# [[SINGLE_ITEM_EXPORT_INT_jens]]
# 0 0 0 0
# [[DEBITOR_LOCATION]]
# 0 1 84 84
# [[EDATA_SERIALNUMBERQUERY_INBOX]]
# 0 0 0 0

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
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


def discover_mq_queues(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[0].startswith("[["):
            yield Service(item=line[0][2:-2])


def check_mq_queues(item: str, params: Mapping[str, Any], section: StringTable) -> CheckResult:
    found = False
    for line in section:
        if found:
            size, consumer_count, enqueue_count, dequeue_count = map(int, line)
            upper = params["consumer_count_levels_upper"] or (None, None)
            lower = params["consumer_count_levels_lower"] or (None, None)
            count_results = list(
                check_levels(
                    consumer_count,
                    None,
                    upper + lower,
                    infoname="Consuming connections",
                    human_readable_func=str,
                )
            )
            if any(isinstance(r, Result) and r.state != State.OK for r in count_results):
                yield from count_results
            yield from check_levels(
                size, "queue", params["size"], infoname="Queue size", human_readable_func=str
            )
            yield from check_levels(
                enqueue_count, "enque", None, infoname="Enqueue count", human_readable_func=str
            )
            yield from check_levels(
                dequeue_count, "deque", None, infoname="Dequeue count", human_readable_func=str
            )
            return

        if line[0].startswith("[[") and line[0][2:-2] == item:
            found = True


def parse_mq_queues(string_table: StringTable) -> StringTable:
    return string_table


agent_section_mq_queues = AgentSection(
    name="mq_queues",
    parse_function=parse_mq_queues,
)


check_plugin_mq_queues = CheckPlugin(
    name="mq_queues",
    service_name="Queue %s",
    discovery_function=discover_mq_queues,
    check_function=check_mq_queues,
    check_ruleset_name="mq_queues",
    check_default_parameters={
        "size": None,
        "consumer_count_levels_upper": None,
        "consumer_count_levels_lower": None,
    },
)
