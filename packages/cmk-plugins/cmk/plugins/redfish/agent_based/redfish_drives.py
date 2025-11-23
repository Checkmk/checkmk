#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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

agent_section_redfish_drives = AgentSection(
    name="redfish_drives",
    parse_function=parse_redfish_multiple,
    parsed_section_name="redfish_drives",
)


def discovery_redfish_drives(section: RedfishAPIData) -> DiscoveryResult:
    for key in section.keys():
        if section[key].get("Status", {}).get("State") == "Absent":
            continue
        if not section[key]["Name"]:
            continue
        item = section[key].get("Id", "0") + "-" + section[key]["Name"]
        yield Service(item=item)


def check_redfish_drives(item: str, section: RedfishAPIData) -> CheckResult:
    data = None
    for key in section.keys():
        if item == section[key].get("Id", "0") + "-" + section[key]["Name"]:
            data = section.get(key, None)
            break
    if data is None:
        return

    disc_msg = (
        f"Size: {(data.get('CapacityBytes', 0) or 0) / 1024 / 1024 / 1024:0.0f}GB, "
        f"Speed {data.get('CapableSpeedGbs', 0)} Gbs"
    )

    if data.get("MediaType") == "SSD":
        if data.get("PredictedMediaLifeLeftPercent"):
            disc_msg = (
                f"{disc_msg}, Media Life Left: {int(data.get('PredictedMediaLifeLeftPercent', 0))}%"
            )
            yield Metric("media_life_left", int(data.get("PredictedMediaLifeLeftPercent")))
        else:
            disc_msg = f"{disc_msg}, no SSD Media information available"

    yield Result(state=State(0), summary=disc_msg)

    dev_state, dev_msg = redfish_health_state(data.get("Status", {}))
    yield Result(state=State(dev_state), notice=dev_msg)


check_plugin_redfish_drives = CheckPlugin(
    name="redfish_drives",
    service_name="Drive %s",
    sections=["redfish_drives"],
    discovery_function=discovery_redfish_drives,
    check_function=check_redfish_drives,
)
