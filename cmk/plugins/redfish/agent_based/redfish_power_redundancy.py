#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.redfish.lib import (
    redfish_health_state,
    RedfishAPIData,
)


def discovery_redfish_power_redundancy(section: RedfishAPIData) -> DiscoveryResult:
    for key in section:
        redundancy = section[key].get("Redundancy")
        if not redundancy:
            continue
        for entry in redundancy:
            mem_id = entry.get("MemberId", "0")
            yield Service(item=mem_id)


def check_redfish_power_redundancy(item: str, section: RedfishAPIData) -> CheckResult:
    for key in section:
        redundancy = section[key].get("Redundancy")
        if not redundancy:
            continue
        for entry in redundancy:
            mem_id = entry.get("MemberId", "0")
            if mem_id != item:
                continue

            dev_state, dev_msg = redfish_health_state(entry.get("Status", {}))
            yield Result(state=State(dev_state), notice=dev_msg)

            name = entry.get("Name", "Unknown")
            mode = entry.get("Mode", "Unknown")
            min_needed = entry.get("MinNumNeeded", "N/A")
            max_supported = entry.get("MaxNumSupported", "N/A")
            psu_count = len(entry.get("RedundancySet", []))

            yield Result(
                state=State.OK,
                summary=f"{name}, Mode: {mode}, "
                f"Min needed: {min_needed}, Max supported: {max_supported}, "
                f"PSUs: {psu_count}",
            )
            return


check_plugin_redfish_power_redundancy = CheckPlugin(
    name="redfish_power_redundancy",
    service_name="Power redundancy %s",
    sections=["redfish_power"],
    discovery_function=discovery_redfish_power_redundancy,
    check_function=check_redfish_power_redundancy,
)
