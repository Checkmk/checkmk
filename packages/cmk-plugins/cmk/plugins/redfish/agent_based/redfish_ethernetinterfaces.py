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


def _render_speed(speed: int) -> str:
    """Render link speed with appropriate unit."""
    if speed >= 1000:
        return f"{speed / 1000:g} Gbps"
    return f"{speed} Mbps"


def discovery_redfish_ethernetinterfaces(
    params: Mapping[str, Any], section: RedfishAPIData
) -> DiscoveryResult:
    """Discover single interfaces"""
    disc_state = params.get("state")
    for key in section:
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

        speed = section[key].get("SpeedMbps", 0)
        if speed == 0:
            speed = section[key].get("CurrentLinkSpeedMbps", 0)

        yield Service(
            item=section[key]["Id"],
            parameters={
                "discover_speed": speed if speed else 0,
                "discover_link_status": section[key].get("LinkStatus", "NOLINK"),
            },
        )


def check_redfish_ethernetinterfaces(
    item: str, params: Mapping[str, Any], section: RedfishAPIData
) -> CheckResult:
    """Check single interfaces"""
    data = section.get(item)
    if data is None:
        return

    # Link status
    link_state = State.OK
    link_summary = "Link: No info"
    if (link_status := data.get("LinkStatus")) is not None:
        link_summary = f"Link: {link_status}"
        discover_link = params.get("discover_link_status")
        if discover_link and discover_link != link_status:
            link_state = State(params.get("state_if_link_status_changed", 2))
            link_summary = f"Link: {link_status} (changed from {discover_link})"
    yield Result(state=link_state, summary=link_summary)

    # Speed
    link_speed = data.get("CurrentLinkSpeedMbps") or data.get("SpeedMbps") or 0
    speed_state = State.OK
    speed_summary = f"Speed: {_render_speed(link_speed)}" if link_speed else "Speed: Unknown"
    discover_speed = params.get("discover_speed")
    if discover_speed and link_speed and discover_speed != link_speed:
        speed_state = State(params.get("state_if_link_speed_changed", 1))
        speed_summary = (
            f"Speed: {_render_speed(link_speed)} (changed from {_render_speed(discover_speed)})"
        )
    yield Result(state=speed_state, summary=speed_summary)

    # MAC address
    mac_addr = ""
    if data.get("AssociatedNetworkAddresses"):
        mac_addr = ", ".join(data.get("AssociatedNetworkAddresses"))
    elif data.get("MACAddress"):
        mac_addr = data.get("MACAddress")
    if mac_addr:
        yield Result(state=State.OK, summary=f"MAC: {mac_addr}")

    # Health state
    if data.get("Status"):
        dev_state, dev_msg = redfish_health_state(data.get("Status", {}))
        yield Result(state=State(dev_state), notice=dev_msg)
    else:
        yield Result(state=State.OK, notice="No known status value found")


check_plugin_redfish_ethernetinterfaces = CheckPlugin(
    name="redfish_ethernetinterfaces",
    service_name="Physical port %s",
    sections=["redfish_ethernetinterfaces"],
    discovery_function=discovery_redfish_ethernetinterfaces,
    discovery_ruleset_name="discovery_redfish_ethernetinterfaces",
    discovery_default_parameters={"state": "updown"},
    check_function=check_redfish_ethernetinterfaces,
    check_ruleset_name="check_redfish_ethernetinterfaces",
    check_default_parameters={},
)
