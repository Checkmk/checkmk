#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This special agent is deprecated. Please use netapp_ontap_if.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    get_value_store,
    register,
    type_defs,
)

from cmk.plugins.lib import interfaces, netapp_api
from cmk.plugins.lib.netapp_api import (
    check_netapp_interfaces,
    IfSection,
    MACList,
    merge_if_sections,
)


def parse_netapp_api_if(  # pylint: disable=too-many-branches
    string_table: type_defs.StringTable,
) -> IfSection:
    ifaces = netapp_api.parse_netapp_api_single_instance(string_table)

    # Dictionary with lists of common mac addresses
    if_mac_list: dict[str, MACList] = {}
    # List of virtual interfaces
    vif_list = []

    speed: str | int

    # Calculate speed, state and create mac-address list
    for name, values in ifaces.items():
        # Reported by 7Mode
        mediatype = values.get("mediatype")
        if mediatype:
            tokens = mediatype.split("-")
            # Possible values according to 7-Mode docu: 100tx | 100tx-fd | 1000fx | 10g-sr
            if "1000" in mediatype:
                speed = 1000000000
            elif "100" in mediatype:
                speed = 100000000
            elif "10g" in mediatype:
                speed = 10000000000
            elif "10" in mediatype:
                speed = 10000000
            else:
                speed = 0
            values["speed"] = str(speed)

            values["state"] = "1" if tokens[-1].lower() == "up" else "2"
        elif values.get("port-role") != "storage-acp":
            # If an interface has no media type and is not a storage-acp, it is considered as
            # virtual interface
            vif_list.append(name)

        # Reported by Clustermode
        for status_key in ["link-status", "operational-status"]:
            if status_key in values:
                if values[status_key] == "up":
                    values["state"] = "1"
                else:
                    values["state"] = "2"
                break

        # Reported by Clustermode
        if "operational-speed" in values:
            raw_speed = values["operational-speed"]
            if raw_speed == "auto":
                # For ONTAP systems, we may receive "auto" for the operational speed
                values["speed"] = raw_speed
            else:
                values["speed"] = str(int(raw_speed) * 1000 * 1000)

        if "mac-address" in values:
            if_mac_list.setdefault(values["mac-address"], [])
            if_mac_list[values["mac-address"]].append((name, values.get("state")))

    return merge_if_sections(ifaces, if_mac_list, vif_list)


register.agent_section(
    name="netapp_api_if",
    parse_function=parse_netapp_api_if,
)


def discover_netapp_api_if(
    params: Sequence[Mapping[str, Any]],
    section: IfSection,
) -> type_defs.DiscoveryResult:
    yield from interfaces.discover_interfaces(
        params,
        section[0],
    )


def check_netapp_api_if(
    item: str,
    params: Mapping[str, Any],
    section: IfSection,
) -> type_defs.CheckResult:
    yield from check_netapp_interfaces(item, params, section, get_value_store(), True)


register.check_plugin(
    name="netapp_api_if",
    service_name="Interface %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=discover_netapp_api_if,
    check_ruleset_name="interfaces",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_netapp_api_if,
)
