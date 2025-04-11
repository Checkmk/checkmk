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

agent_section_redfish_physicaldrives = AgentSection(
    name="redfish_physicaldrives",
    parse_function=parse_redfish_multiple,
    parsed_section_name="redfish_physicaldrives",
)


def _item_names(section: RedfishAPIData) -> dict:
    """
    Create a dictionary with the item name as key and the data as value.
    The item name is created by concatenating the controller ID and the
    Location or Name of the drive.
    If the Location is empty, the Name is used.
    """
    new_data = {}
    for _key, data in section.items():
        loc = data.get("Location")
        if loc == []:
            path = data.get("@odata.id").split("/")[1:]
            controller_id = path[-3:-2][0]
            item = controller_id + ":" + data.get("Name")
        else:
            path = data.get("@odata.id").split("/")[1:]
            controller_id = path[-3:-2][0]
            item = controller_id + ":" + data["Location"]
        new_data[item] = data

    return new_data


def discovery_redfish_physicaldrives(section: RedfishAPIData) -> DiscoveryResult:
    raw_data = _item_names(section)
    for key in raw_data:
        yield Service(item=key)


def check_redfish_physicaldrives(item: str, section: RedfishAPIData) -> CheckResult:
    raw_data = _item_names(section)
    data = raw_data.get(item, None)
    if data is None:
        return

    capacity = data.get("CapacityBytes", None)
    if not capacity:
        capacity = data.get("CapacityMiB", None)
        if capacity:
            capacity = capacity / 1024
    else:
        capacity = capacity / 1024 / 1024 / 1024

    speed = data.get("CapableSpeedGbs", None)
    if not speed:
        speed = data.get("InterfaceSpeedMbps", 0)
        speed = speed / 1000

    disc_msg = f"Size: {capacity:0.0f}GB, Speed {speed} Gbs"

    if data.get("MediaType") == "SSD":
        if data.get("PredictedMediaLifeLeftPercent"):
            disc_msg = (
                f"{disc_msg}, Media Life Left: "
                f"{int(data.get('PredictedMediaLifeLeftPercent', 0))}%"
            )
            yield Metric("media_life_left", int(data.get("PredictedMediaLifeLeftPercent")))
        elif data.get("SSDEnduranceUtilizationPercentage"):
            disc_msg = (
                f"{disc_msg}, SSD Utilization: "
                f"{int(data.get('SSDEnduranceUtilizationPercentage', 0))}%"
            )
            yield Metric("ssd_utilization", int(data.get("SSDEnduranceUtilizationPercentage")))
    yield Result(state=State(0), summary=disc_msg)

    dev_state, dev_msg = redfish_health_state(data.get("Status", {}))
    status = dev_state
    message = dev_msg
    yield Result(state=State(status), notice=message)

    dev_ser = data.get("SerialNumber")
    dev_mod = data.get("Model")
    yield Result(state=State(0), notice=f"Serial: {dev_ser}\nModel: {dev_mod}")

    if data.get("CurrentTemperatureCelsius", None):
        yield Metric("temp", int(data.get("CurrentTemperatureCelsius")))


check_plugin_redfish_physicaldrives = CheckPlugin(
    name="redfish_physicaldrives",
    service_name="Drive %s",
    sections=["redfish_physicaldrives"],
    discovery_function=discovery_redfish_physicaldrives,
    check_function=check_redfish_physicaldrives,
)
