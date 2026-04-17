#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check individual power supplies (modern Redfish PowerSubsystem/PowerSupplies model)"""

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

agent_section_redfish_powersupplies = AgentSection(
    name="redfish_powersupplies",
    parse_function=parse_redfish_multiple,
    parsed_section_name="redfish_powersupplies",
)


def discovery_redfish_powersupplies(section: RedfishAPIData) -> DiscoveryResult:
    for key in section:
        if section[key].get("Status", {}).get("State") in ("Absent", "Disabled"):
            continue
        yield Service(item=key)


def check_redfish_powersupplies(item: str, section: RedfishAPIData) -> CheckResult:
    data = section.get(item)
    if data is None:
        return

    manufacturer = data.get("Manufacturer", "Unknown")
    model = data.get("Model", "Unknown")
    firmware = data.get("FirmwareVersion", "")
    line_status = data.get("LineInputStatus", "Unknown")

    capacity = None
    for input_range in data.get("InputRanges", []):
        if (cap := input_range.get("CapacityWatts")) is not None:
            capacity = float(cap)
            break

    details: list[str] = [f"{manufacturer} {model}"]
    if firmware:
        details.append(f"FW: {firmware}")
    if capacity is not None:
        details.append(f"Capacity: {capacity:.0f} W")
    details.append(f"Line input: {line_status}")

    yield Result(state=State.OK, summary=", ".join(details))

    if capacity is not None:
        yield Metric("power_capacity", capacity)

    dev_state, dev_msg = redfish_health_state(data.get("Status", {}))
    yield Result(state=State(dev_state), notice=dev_msg)


check_plugin_redfish_powersupplies = CheckPlugin(
    name="redfish_powersupplies",
    service_name="Power supply %s",
    sections=["redfish_powersupplies"],
    discovery_function=discovery_redfish_powersupplies,
    check_function=check_redfish_powersupplies,
)
