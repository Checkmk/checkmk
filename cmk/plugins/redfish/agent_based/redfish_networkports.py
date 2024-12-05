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

agent_section_redfish_networkports = AgentSection(
    name="redfish_networkports",
    parse_function=parse_redfish_multiple,
    parsed_section_name="redfish_networkports",
)


def discovery_redfish_networkports(section: RedfishAPIData) -> DiscoveryResult:
    for key in section.keys():
        yield Service(item=section[key]["Id"])


def check_redfish_networkports(item: str, section: RedfishAPIData) -> CheckResult:
    data = section.get(item, None)
    if data is None:
        return

    linkspeed = data.get("CurrentLinkSpeedMbps", 0)
    if linkspeed is None:
        linkspeed = 0

    int_msg = (
        f"Link: {data.get('LinkStatus')}, Speed: {linkspeed:0.0f}Mbps, "
        f"MAC: {', '.join(data.get('AssociatedNetworkAddresses'))}"
    )
    yield Result(state=State(0), summary=int_msg)

    dev_state, dev_msg = redfish_health_state(data.get("Status", {}))
    status = dev_state
    message = dev_msg

    yield Result(state=State(status), notice=message)


check_plugin_redfish_networkports = CheckPlugin(
    name="redfish_networkports",
    service_name="Physical port %s",
    sections=["redfish_networkports"],
    discovery_function=discovery_redfish_networkports,
    check_function=check_redfish_networkports,
)
