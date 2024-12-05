#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
    redfish_item_hpe,
    RedfishAPIData,
)

agent_section_redfish_logicaldrives = AgentSection(
    name="redfish_logicaldrives",
    parse_function=parse_redfish_multiple,
    parsed_section_name="redfish_logicaldrives",
)


def discovery_redfish_logicaldrives(section: RedfishAPIData) -> DiscoveryResult:
    """One service per logical drive is discovered"""
    for key in section.keys():
        if "SmartStorageLogicalDrive" in section[key].get("@odata.type"):
            item = redfish_item_hpe(section[key])
        else:
            item = section[key]["Id"]
        yield Service(item=item)


def check_redfish_logicaldrives(item: str, section: RedfishAPIData) -> CheckResult:
    """Check the state of a logical drive"""
    data = section.get(item, None)
    if data is None:
        return

    raid_type = data.get("RAIDType", None)
    if not raid_type:
        raid_type = f"RAID{data.get('Raid', ' Unknown')}"

    size = data.get("CapacityBytes")
    if not size:
        size = data.get("CapacityMiB") / 1024
    else:
        size = size / 1024 / 1024 / 1024

    volume_msg = f"Raid Type: {raid_type}, Size: {size:0.0f}GB"
    yield Result(state=State(0), summary=volume_msg)

    dev_state, dev_msg = redfish_health_state(data.get("Status", {}))
    status = dev_state
    message = dev_msg

    yield Result(state=State(status), notice=message)


check_plugin_redfish_logicaldrives = CheckPlugin(
    name="redfish_logicaldrives",
    service_name="Volume %s",
    sections=["redfish_logicaldrives"],
    discovery_function=discovery_redfish_logicaldrives,
    check_function=check_redfish_logicaldrives,
)
