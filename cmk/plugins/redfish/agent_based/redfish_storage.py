#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.redfish.lib import (
    parse_redfish_multiple,
    redfish_health_state,
    RedfishAPIData,
)

agent_section_redfish_storage = AgentSection(
    name="redfish_storage",
    parse_function=parse_redfish_multiple,
    parsed_section_name="redfish_storage",
)


def discovery_redfish_storage(section: RedfishAPIData) -> DiscoveryResult:
    """Discover single controllers"""
    for key in section:
        if section[key].get("Status", {}).get("State") == "UnavailableOffline":
            continue
        yield Service(item=section[key]["Id"])


def check_redfish_storage(
    item: str, params: Mapping[str, Any], section: RedfishAPIData
) -> CheckResult:
    """Check single Controller state"""
    data = section.get(item)
    if data is None:
        return

    check_type = params.get("check_type", "full")

    # Rollup mode: only report overall health
    if check_type == "rollup":
        dev_state, dev_msg = redfish_health_state(data.get("Status", {}))
        yield Result(state=State(dev_state), summary=dev_msg)
        return

    # Full mode: detailed controller info
    controller_list = data.get("StorageControllers", [])
    if len(controller_list) == 1:
        for ctrl_data in controller_list:
            storage_msg = (
                f"Type: {ctrl_data.get('Model')}, "
                f"RaidLevels: {','.join(ctrl_data.get('SupportedRAIDTypes', []))}, "
                f"DeviceProtocols: {','.join(ctrl_data.get('SupportedDeviceProtocols', []))}"
            )
            dev_state, dev_msg = redfish_health_state(ctrl_data.get("Status", {}))
            yield Result(state=State(dev_state), summary=storage_msg, details=dev_msg)
    elif len(controller_list) > 1:
        global_state = 0
        global_msg = ""
        for ctrl_data in controller_list:
            storage_msg = (
                f"Type: {ctrl_data.get('Model')}, "
                f"RaidLevels: {','.join(ctrl_data.get('SupportedRAIDTypes', []))}, "
                f"DeviceProtocols: {','.join(ctrl_data.get('SupportedDeviceProtocols', []))}"
            )
            dev_state, dev_msg = redfish_health_state(ctrl_data.get("Status", {}))
            global_state = max(global_state, dev_state)
            yield Result(state=State(dev_state), details=storage_msg, notice=dev_msg)
        if global_state != 0:
            global_msg = "One or more controllers with problems"
        else:
            global_msg = "All controllers are working properly"
        yield Result(state=State(global_state), summary=global_msg)
    else:
        dev_state, dev_msg = redfish_health_state(data.get("Status", {}))
        yield Result(state=State(dev_state), notice=dev_msg)


def discovery_redfish_storage_battery(section: RedfishAPIData) -> DiscoveryResult:
    """Discover Dell storage controller batteries."""
    for key in section:
        if section[key].get("Status", {}).get("State") == "UnavailableOffline":
            continue
        battery_data = ((section[key].get("Oem") or {}).get("Dell") or {}).get(
            "DellControllerBattery"
        )
        if battery_data is not None:
            yield Service(item=section[key]["Id"])


def check_redfish_storage_battery(item: str, section: RedfishAPIData) -> CheckResult:
    """Check Dell storage controller battery state."""
    data = section.get(item)
    if data is None:
        return

    battery_data = ((data.get("Oem") or {}).get("Dell") or {}).get("DellControllerBattery")
    if not battery_data:
        return

    batt_name = battery_data.get("Name", "Controller Battery")
    primary_status = battery_data.get("PrimaryStatus", "Unknown")
    raid_state = battery_data.get("RAIDState", "Unknown")

    _battery_status_map = {"OK": State.OK, "Warning": State.WARN, "Degraded": State.WARN}
    state = _battery_status_map.get(primary_status, State.CRIT)
    yield Result(
        state=state,
        summary=f"{batt_name} state: {primary_status}, RAID Status: {raid_state}",
    )


check_plugin_redfish_storage = CheckPlugin(
    name="redfish_storage",
    service_name="Storage controller %s",
    sections=["redfish_storage"],
    discovery_function=discovery_redfish_storage,
    check_function=check_redfish_storage,
    check_ruleset_name="redfish_storage",
    check_default_parameters={},
)

check_plugin_redfish_storage_battery = CheckPlugin(
    name="redfish_storage_battery",
    service_name="Storage controller %s battery",
    sections=["redfish_storage"],
    discovery_function=discovery_redfish_storage_battery,
    check_function=check_redfish_storage_battery,
)
