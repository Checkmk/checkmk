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

agent_section_redfish_volumes = AgentSection(
    name="redfish_volumes",
    parse_function=parse_redfish_multiple,
    parsed_section_name="redfish_volumes",
)


def _build_volume_item(data: RedfishAPIData) -> tuple[str, str]:
    """Build classic and ctrlid item names for a volume.

    Classic: just the Id field
    Ctrlid: structured from OData path (e.g., "0:1:4" from
            /redfish/v1/Systems/0/Storage/1/Volumes/4)
    """
    classic = data.get("Id", "")
    odata_id = data.get("@odata.id", "")
    if odata_id:
        parts = odata_id.strip("/").split("/")
        if len(parts) >= 7 and "Volumes" in parts:
            vol_idx = parts.index("Volumes")
            if vol_idx >= 4:
                ctrlid = ":".join(parts[3:vol_idx:2] + [parts[vol_idx + 1]])
            else:
                ctrlid = ":".join(parts[-2:])
        else:
            ctrlid = classic
    else:
        ctrlid = classic
    return classic, ctrlid


def discovery_redfish_volumes(
    params: Mapping[str, Any], section: RedfishAPIData
) -> DiscoveryResult:
    naming = params.get("item", "classic")
    for key in section:
        classic, ctrlid = _build_volume_item(section[key])
        item = ctrlid if naming == "ctrlid" else classic
        yield Service(item=item)


def check_redfish_volumes(item: str, section: RedfishAPIData) -> CheckResult:
    data = None
    for key in section:
        classic, ctrlid = _build_volume_item(section[key])
        if item in (classic, ctrlid):
            data = section[key]
            break
    if data is None:
        return

    volume_msg = (
        f"Raid Type: {data.get('RAIDType', None)}, "
        f"Size: {int(data.get('CapacityBytes', 0.0)) / 1024 / 1024 / 1024:0.1f}GB"
    )
    yield Result(state=State(0), summary=volume_msg)

    dev_state, dev_msg = redfish_health_state(data.get("Status", {}))
    yield Result(state=State(dev_state), notice=dev_msg)


check_plugin_redfish_volumes = CheckPlugin(
    name="redfish_volumes",
    service_name="Volume %s",
    sections=["redfish_volumes"],
    discovery_function=discovery_redfish_volumes,
    discovery_ruleset_name="discovery_redfish_volumes",
    discovery_default_parameters={"item": "classic"},
    check_function=check_redfish_volumes,
)
