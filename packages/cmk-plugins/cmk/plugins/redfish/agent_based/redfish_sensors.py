#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""check single redfish sensor state"""

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    State,
)
from cmk.plugins.lib.humidity import (
    check_humidity,
)
from cmk.plugins.lib.temperature import (
    check_temperature,
    TempParamDict,
)
from cmk.plugins.redfish.lib import (
    parse_redfish_multiple,
    process_redfish_perfdata,
    redfish_health_state,
    RedfishAPIData,
)

agent_section_redfish_sensors = AgentSection(
    name="redfish_sensors",
    parse_function=parse_redfish_multiple,
    parsed_section_name="redfish_sensors",
)


def discovery_redfish_sensors(section: RedfishAPIData) -> DiscoveryResult:
    """Discover single sensors"""
    for key in section.keys():
        if section[key].get("Status", {}).get("State") == "Absent":
            continue
        yield Service(item=section[key]["Id"])


def check_redfish_sensors(item: str, params: TempParamDict, section: RedfishAPIData) -> CheckResult:
    """Check single sensor state"""
    data = section.get(item)
    if data is None:
        return

    perfdata = process_redfish_perfdata(data)
    if perfdata:
        if data.get("ReadingType") == "Temperature":
            yield from check_temperature(
                perfdata.value,
                params,
                unique_name=f"redfish.temp.{item}",
                value_store=get_value_store(),
                dev_levels=(
                    perfdata.levels_upper[1]
                    if perfdata.levels_upper and len(perfdata.levels_upper) > 1
                    else None
                ),
                dev_levels_lower=(
                    perfdata.levels_lower[1]
                    if perfdata.levels_lower and len(perfdata.levels_lower) > 1
                    else None
                ),
            )
        elif data.get("ReadingType") == "Humidity":
            yield from check_humidity(
                humidity=perfdata.value,
                params={
                    "levels": (
                        perfdata.levels_upper[1]
                        if perfdata.levels_upper and len(perfdata.levels_upper) > 1
                        else None
                    ),
                    "levels_lower": (
                        perfdata.levels_lower[1]
                        if perfdata.levels_lower and len(perfdata.levels_lower) > 1
                        else None
                    ),
                },
            )
    else:
        yield Result(state=State(0), summary="No temperature data found")

    dev_state, dev_msg = redfish_health_state(data.get("Status", {}))
    yield Result(state=State(dev_state), notice=dev_msg)


check_plugin_redfish_sensors = CheckPlugin(
    name="redfish_sensors",
    service_name="Sensor %s",
    sections=["redfish_sensors"],
    discovery_function=discovery_redfish_sensors,
    check_function=check_redfish_sensors,
    check_default_parameters={},
    check_ruleset_name="temperature",
)
