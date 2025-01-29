#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""check single redfish outlet state"""

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.lib.elphase import check_elphase
from cmk.plugins.redfish.lib import (
    parse_redfish_multiple,
    redfish_health_state,
    RedfishAPIData,
)

agent_section_redfish_outlets = AgentSection(
    name="redfish_outlets",
    parse_function=parse_redfish_multiple,
    parsed_section_name="redfish_outlets",
)


def discovery_redfish_outlets(
    params: Mapping[str, Any], section: RedfishAPIData
) -> DiscoveryResult:
    """Discover single sensors"""
    for key in section.keys():
        if section[key].get("Status", {}).get("State") == "Absent":
            continue
        outlet_name = params.get("naming")
        if outlet_name == "index":
            yield Service(item=section[key]["Id"])
        elif outlet_name == "label":
            if section[key]["UserLabel"]:
                item_name = f"{section[key]['Id']}-{section[key]['UserLabel']}"
            else:
                item_name = section[key]["Id"]
            yield Service(item=item_name)
        elif outlet_name == "fill":
            padding = len(str(len(section)))
            yield Service(item=section[key].get("Id").zfill(padding))


def check_redfish_outlets(
    item: str, params: Mapping[str, Any], section: RedfishAPIData
) -> CheckResult:
    """Check single outlet state"""
    if item.startswith("0"):
        section_id = item
        while True:
            section_id = section_id[1:]
            if not section_id.startswith("0"):
                break
    elif item.isdigit():
        section_id = item
    elif len(item.split("-")) == 2:
        section_id = item.split("-")[0]

    data = section.get(section_id, None)
    if data is None:
        return

    socket_data = {
        item: {
            "voltage": data.get("Voltage", {}).get("Reading"),
            "current": data.get("CurrentAmps", {}).get("Reading"),
            "power": data.get("PowerWatts", {}).get("Reading"),
            "frequency": data.get("FrequencyHz", {}).get("Reading"),
        }
    }

    if all(value is not None for value in socket_data[item].values()):
        yield from check_elphase(item, params, socket_data)

    if data.get("EnergykWh", {}).get("Reading") is not None:
        energy = data.get("EnergykWh", {}).get("Reading")
        yield from check_levels(
            energy,
            metric_name="energy",
            label="Energy",
            render_func=lambda v: f"{v:.1f} kWh",
        )

    dev_state, dev_msg = redfish_health_state(data.get("Status", {}))
    yield Result(state=State(dev_state), notice=dev_msg)


check_plugin_redfish_outlets = CheckPlugin(
    name="redfish_outlets",
    service_name="Outlet %s",
    sections=["redfish_outlets"],
    discovery_function=discovery_redfish_outlets,
    discovery_ruleset_name="discovery_redfish_outlets",
    discovery_default_parameters={"naming": "index"},
    check_function=check_redfish_outlets,
    check_default_parameters={},
    check_ruleset_name="ups_outphase",
)
