#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
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

agent_section_redfish_rackpdus = AgentSection(
    name="redfish_rackpdus",
    parse_function=parse_redfish_multiple,
    parsed_section_name="redfish_rackpdus",
)


def discovery_redfish_pdus(section: RedfishAPIData) -> DiscoveryResult:
    for key in section:
        yield Service(item=section[key].get("Id", key))


def check_redfish_pdus(item: str, section: RedfishAPIData) -> CheckResult:
    data = None
    for key in section:
        if section[key].get("Id", key) == item:
            data = section[key]
            break
    if data is None:
        return

    details_parts = []
    if firmware := data.get("FirmwareVersion"):
        details_parts.append(f"Firmware: {firmware}")
    if serial := data.get("SerialNumber"):
        details_parts.append(f"Serial: {serial}")
    if model := data.get("Model"):
        details_parts.append(f"Model: {model}")
    if manufacturer := data.get("Manufacturer"):
        details_parts.append(f"Manufacturer: {manufacturer}")

    if details_parts:
        yield Result(state=State.OK, summary=", ".join(details_parts))

    dev_state, dev_msg = redfish_health_state(data.get("Status", {}))
    yield Result(state=State(dev_state), notice=dev_msg)


check_plugin_redfish_pdus = CheckPlugin(
    name="redfish_pdus",
    service_name="PDU %s",
    sections=["redfish_rackpdus"],
    discovery_function=discovery_redfish_pdus,
    check_function=check_redfish_pdus,
)
