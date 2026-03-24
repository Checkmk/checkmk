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


def _build_drive_item(data: RedfishAPIData) -> tuple[str, str]:
    """Build classic and ctrlid item names for a drive.

    Classic: "Id-Name" (e.g., "0-1.2TB 12G SAS HDD")
    Ctrlid: structured from OData path (e.g., "0:1:4" from
            /redfish/v1/Systems/0/Storage/1/Drives/4)
    """
    classic = data.get("Id", "0") + "-" + data.get("Name", "")
    odata_id = data.get("@odata.id", "")
    if odata_id:
        parts = odata_id.strip("/").split("/")
        # Try to extract system:storage:drive or chassis:drive format
        if len(parts) >= 7 and "Drives" in parts:
            drive_idx = parts.index("Drives")
            if drive_idx >= 4:
                # e.g., /redfish/v1/Systems/0/Storage/1/Drives/4 -> 0:1:4
                ctrlid = ":".join(parts[3:drive_idx:2] + [parts[drive_idx + 1]])
            else:
                ctrlid = ":".join(parts[-2:])
        elif len(parts) >= 5:
            # e.g., /redfish/v1/Chassis/DE00B000/Drives/0 -> DE00B000:0
            ctrlid = ":".join(parts[-2:])
        else:
            ctrlid = classic
    else:
        ctrlid = classic
    return classic, ctrlid


def discovery_redfish_drives(params: Mapping[str, Any], section: RedfishAPIData) -> DiscoveryResult:
    naming = params.get("item", "classic")
    for key in section:
        if section[key].get("Status", {}).get("State") == "Absent":
            continue
        if not section[key].get("Name"):
            continue
        classic, ctrlid = _build_drive_item(section[key])
        item = ctrlid if naming == "ctrlid" else classic
        yield Service(item=item)


def check_redfish_drives(item: str, section: RedfishAPIData) -> CheckResult:
    data = None
    for key in section:
        classic, ctrlid = _build_drive_item(section[key])
        if item in (classic, ctrlid):
            data = section.get(key)
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
    discovery_ruleset_name="discovery_redfish_drives",
    discovery_default_parameters={"item": "classic"},
    check_function=check_redfish_drives,
)
