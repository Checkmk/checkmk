#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk_addons.plugins.redfish.lib import (
    RedfishAPIData,
    redfish_health_state,
)


def discover_redfish_memory_summary(section: RedfishAPIData) -> DiscoveryResult:
    if len(section) == 1:
        for element in section:
            if "MemorySummary" in element.keys():
                yield Service(item="Summary")
    else:
        for element in section:
            if "MemorySummary" in element.keys():
                item = f"Summary {element.get('Id', '0')}"
                yield Service(item=item)


def check_redfish_memory_summary(item: str, section: RedfishAPIData) -> CheckResult:
    result = None
    if len(section) == 1:
        result = section[0].get("MemorySummary")
    else:
        for element in section:
            if "MemorySummary" in element.keys():
                if item == f"Summary {element.get('Id', '0')}":
                    result = element.get("MemorySummary")
                    break

    if not result:
        return

    state = result.get("Status", {"Health": "Unknown"})
    result_state, state_text = redfish_health_state(state)
    message = (
        f"Capacity: {result.get('TotalSystemMemoryGiB')}GB, with State: {state_text}"
    )

    yield Result(state=State(result_state), summary=message)


check_plugin_redfish_memory_summary = CheckPlugin(
    name="redfish_memory_summary",
    service_name="Memory %s",
    sections=["redfish_system"],
    discovery_function=discover_redfish_memory_summary,
    check_function=check_redfish_memory_summary,
)
