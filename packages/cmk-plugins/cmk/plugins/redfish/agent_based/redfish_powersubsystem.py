#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check power subsystem redundancy and capacity (modern Redfish resource model)"""

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
)
from cmk.plugins.redfish.lib import (
    parse_redfish_multiple,
    redfish_health_state,
    RedfishAPIData,
)

agent_section_redfish_powersubsystem = AgentSection(
    name="redfish_powersubsystem",
    parse_function=parse_redfish_multiple,
    parsed_section_name="redfish_powersubsystem",
)


def discovery_redfish_powersubsystem(section: RedfishAPIData) -> DiscoveryResult:
    for key in section:
        yield Service(item=key)


def check_redfish_powersubsystem(item: str, section: RedfishAPIData) -> CheckResult:
    data = section.get(item)
    if data is None:
        return

    dev_state, dev_msg = redfish_health_state(data.get("Status", {}))
    yield Result(state=State(dev_state), summary=dev_msg)

    if (capacity := data.get("CapacityWatts")) is not None:
        yield Metric("power_capacity", capacity)
        yield Result(state=State.OK, notice=f"Total PSU capacity: {capacity:.0f} W")

    allocation = data.get("Allocation", {})
    if (allocated := allocation.get("AllocatedWatts")) is not None:
        yield Result(state=State.OK, notice=f"Allocated: {allocated:.0f} W")

    for redundancy in data.get("PowerSupplyRedundancy", []):
        red_state, red_msg = redfish_health_state(redundancy.get("Status", {}))
        red_type = redundancy.get("RedundancyType", "Unknown")
        min_needed = redundancy.get("MinNeededInGroup", "?")
        max_supported = redundancy.get("MaxSupportedInGroup", "?")
        num_present = len(redundancy.get("RedundancyGroup", []))
        yield Result(
            state=State(red_state),
            summary=(
                f"Redundancy: {red_type}, {num_present} of {max_supported} present "
                f"(min {min_needed} needed), {red_msg}"
            ),
        )


check_plugin_redfish_powersubsystem = CheckPlugin(
    name="redfish_powersubsystem",
    service_name="Power Subsystem %s",
    sections=["redfish_powersubsystem"],
    discovery_function=discovery_redfish_powersubsystem,
    check_function=check_redfish_powersubsystem,
)
