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
    RedfishAPIData,
)

agent_section_redfish_volumes = AgentSection(
    name="redfish_volumes",
    parse_function=parse_redfish_multiple,
    parsed_section_name="redfish_volumes",
)


def discovery_redfish_volumes(section: RedfishAPIData) -> DiscoveryResult:
    for key in section.keys():
        yield Service(item=section[key]["Id"])


def check_redfish_volumes(item: str, section: RedfishAPIData) -> CheckResult:
    data = section.get(item, None)
    if data is None:
        return
    volume_msg = (
        f"Raid Type: {data.get('RAIDType', None)}, "
        f"Size: {int(data.get('CapacityBytes', 0.0)) / 1024 / 1024 / 1024:0.1f}GB"
    )
    yield Result(state=State(0), summary=volume_msg)

    dev_state, dev_msg = redfish_health_state(data.get("Status", {}))
    status = dev_state
    message = dev_msg

    yield Result(state=State(status), notice=message)


check_plugin_redfish_volumes = CheckPlugin(
    name="redfish_volumes",
    service_name="Volume %s",
    sections=["redfish_volumes"],
    discovery_function=discovery_redfish_volumes,
    check_function=check_redfish_volumes,
)
