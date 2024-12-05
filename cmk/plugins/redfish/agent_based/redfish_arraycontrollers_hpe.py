#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
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


def discovery_redfish_arraycontrollers_hpe(section: RedfishAPIData) -> DiscoveryResult:
    for key in section.keys():
        if "SmartStorageArrayController" in section[key]["@odata.type"]:
            yield Service(item=section[key]["Id"])


def check_redfish_arraycontrollers_hpe(item: str, section: RedfishAPIData) -> CheckResult:
    data = section.get(item, None)
    if data is None:
        return

    dev_type = data.get("Model")
    dev_ser = data.get("SerialNumber")

    storage_msg = f"Type: {dev_type}, Serial: {dev_ser}"
    yield Result(state=State(0), summary=storage_msg)

    dev_state, dev_msg = redfish_health_state(data.get("Status", {}))
    status = dev_state
    message = dev_msg

    yield Result(state=State(status), notice=message)


check_plugin_redfish_arraycontrollers_hpe = CheckPlugin(
    name="redfish_arraycontrollers_hpe",
    service_name="Storage Controller %s",
    sections=["redfish_arraycontrollers"],
    discovery_function=discovery_redfish_arraycontrollers_hpe,
    check_function=check_redfish_arraycontrollers_hpe,
)
