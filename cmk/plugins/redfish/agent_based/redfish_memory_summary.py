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
from cmk.plugins.redfish.lib import (
    redfish_health_state,
    RedfishAPIData,
)


def discover_redfish_memory_summary(section: RedfishAPIData) -> DiscoveryResult:
    # FIXME: If this works, the section must look completely different
    if len(section) == 1:
        for element in section:
            if "MemorySummary" in element.keys():  # type: ignore[attr-defined]
                yield Service(item="Summary")
    else:
        for element in section:
            if "MemorySummary" in element.keys():  # type: ignore[attr-defined]
                item = f"Summary {element.get('Id', '0')}"  # type: ignore[attr-defined]
                yield Service(item=item)


def check_redfish_memory_summary(item: str, section: RedfishAPIData) -> CheckResult:
    result = None
    if len(section) == 1:
        result = section[0].get("MemorySummary")  # type: ignore[index]
    else:
        for element in section:
            if "MemorySummary" in element.keys():  # type: ignore[attr-defined]
                if item == f"Summary {element.get('Id', '0')}":  # type: ignore[attr-defined]
                    result = element.get("MemorySummary")  # type: ignore[attr-defined]
                    break

    if not result:
        return

    state = result.get("Status", {"Health": "Unknown"})
    result_state, state_text = redfish_health_state(state)
    message = f"Capacity: {result.get('TotalSystemMemoryGiB')}GB, with State: {state_text}"

    yield Result(state=State(result_state), summary=message)


check_plugin_redfish_memory_summary = CheckPlugin(
    name="redfish_memory_summary",
    service_name="Memory %s",
    sections=["redfish_system"],
    discovery_function=discover_redfish_memory_summary,
    check_function=check_redfish_memory_summary,
)
