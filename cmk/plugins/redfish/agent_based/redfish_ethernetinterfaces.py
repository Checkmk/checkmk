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

agent_section_redfish_ethernetinterfaces = AgentSection(
    name="redfish_ethernetinterfaces",
    parse_function=parse_redfish_multiple,
    parsed_section_name="redfish_ethernetinterfaces",
)


def discovery_redfish_ethernetinterfaces(
    params: Mapping[str, Any], section: RedfishAPIData
) -> DiscoveryResult:
    """Discover single interfaces"""
    disc_state = params.get("state")
    for key in section.keys():
        if not section[key].get("Status"):
            continue
        if section[key].get("Status", {}).get("State") in [
            "Absent",
            "Disabled",
            "Offline",
            "UnavailableOffline",
            "StandbyOffline",
        ]:
            continue
        if section[key].get("LinkStatus", "NOLINK") in ["LinkDown"] and disc_state == "up":
            continue
        if section[key].get("LinkStatus", "NOLINK") in ["LinkUp"] and disc_state == "down":
            continue
        yield Service(item=section[key]["Id"])


def check_redfish_ethernetinterfaces(item: str, section: RedfishAPIData) -> CheckResult:
    """Check single interfaces"""
    data = section.get(item, None)
    if data is None:
        return

    mac_addr = ""
    if data.get("AssociatedNetworkAddresses"):
        mac_addr = ", ".join(data.get("AssociatedNetworkAddresses"))
    elif data.get("MACAddress"):
        mac_addr = data.get("MACAddress")

    link_speed = 0
    if data.get("CurrentLinkSpeedMbps"):
        link_speed = data.get("CurrentLinkSpeedMbps")
    elif data.get("SpeedMbps"):
        link_speed = data.get("SpeedMbps")
    if link_speed is None:
        link_speed = 0

    link_status = "Unknown"
    if data.get("LinkStatus"):
        link_status = data.get("LinkStatus")
        if link_status is None:
            link_status = "Down"

    int_msg = f"Link: {link_status}, Speed: {link_speed:0.0f}Mbps, MAC: {mac_addr}"
    yield Result(state=State(0), summary=int_msg)

    if data.get("Status"):
        dev_state, dev_msg = redfish_health_state(data.get("Status", {}))
        status = dev_state
        message = dev_msg
    else:
        status = 0
        message = "No known status value found"

    yield Result(state=State(status), notice=message)


check_plugin_redfish_ethernetinterfaces = CheckPlugin(
    name="redfish_ethernetinterfaces",
    service_name="Physical port %s",
    sections=["redfish_ethernetinterfaces"],
    discovery_function=discovery_redfish_ethernetinterfaces,
    discovery_ruleset_name="discovery_redfish_ethernetinterfaces",
    discovery_default_parameters={"state": "updown"},
    check_function=check_redfish_ethernetinterfaces,
)
