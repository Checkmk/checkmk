#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

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
        if section[key].get("Redundancy"):
            yield Service()
            return


def check_redfish_power_redundancy(section: RedfishAPIData) -> CheckResult:
    redundancy: list[Mapping[str, Any]] = []
    for key in section:
        if redundancy_element := section[key].get("Redundancy"):
            redundancy.extend(redundancy_element)

    if not redundancy:
        return

    for element in redundancy:
        dev_state, dev_msg = redfish_health_state(element.get("Status", {}))
        yield Result(state=State(dev_state), summary=dev_msg)
        details_msg: list[str] = []
        for attr in ["Name", "Mode", "MinNumNeeded", "MaxNumSupported"]:
            if value := element.get(attr):
                details_msg.append(f"{attr}: {value}")
        if (num_ps := len(element.get("RedundancySet") or [])) > 0:
            details_msg.append(f"Number of Power Supplies in Redundancy Set: {num_ps}")

        if details_msg:
            yield Result(state=State.OK, notice="\n".join(details_msg))


check_plugin_redfish_power_redundancy = CheckPlugin(
    name="redfish_power_redundancy",
    service_name="Power redundancy",
    sections=["redfish_power"],
    discovery_function=discovery_redfish_power_redundancy,
    check_function=check_redfish_power_redundancy,
)
