#!/usr/bin/env python3
'''check single redfish sensor state'''
# -*- encoding: utf-8; py-indent-offset: 4 -*-

# (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>

# License: GNU General Public License v2

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    get_value_store,
)
from cmk.plugins.redfish.lib import (
    RedfishAPIData,
    parse_redfish_multiple,
    process_redfish_perfdata,
    redfish_health_state,
)
from cmk.plugins.lib.temperature import (
    check_temperature,
    TempParamDict,
)
from cmk.plugins.lib.humidity import (
    check_humidity,
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


def check_redfish_sensors(
    item: str, params: TempParamDict, section: RedfishAPIData
) -> CheckResult:
    """Check single sensor state"""
    data = section.get(item, None)
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
                params={"levels": (
                    perfdata.levels_upper[1]
                    if perfdata.levels_upper and len(perfdata.levels_upper) > 1
                    else None
                ), "levels_lower": (
                    perfdata.levels_lower[1]
                    if perfdata.levels_lower and len(perfdata.levels_lower) > 1
                    else None
                )},
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
