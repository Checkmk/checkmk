#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# Note: Sometimes the esx_vsphere_sensors check reports incorrect sensor data.
# The reason is that the data is cached on the esx system. In the worst case some sensors
# might get stuck in an unhealthy state. You can find more information under the following link:
# http://kb.vmware.com/selfservice/microsites/search.do?cmd=displayKC&externalId=1037330

# <<<esx_vsphere_sensors:sep(59)>>>
# VMware Rollup Health State;;0;system;0;;red;Red;Sensor is operating under critical conditions
# Power Domain 1 Power Unit 0 - Redundancy lost;;0;power;0;;yellow;Yellow;Sensor is operating under conditions that are non-critical
# Power Supply 2 Power Supply 2 0: Power Supply AC lost - Assert;;0;power;0;;red;Red;Sensor is operating under critical conditions


from collections.abc import Mapping
from typing import Any, Final

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

type _Section = StringTable


_SENSOR_STATES: Final = {
    "green": State.OK,
    "yellow": State.WARN,
    "red": State.CRIT,
    "unknown": State.UNKNOWN,
}


def discover_esx_vsphere_sensors(section: _Section) -> DiscoveryResult:
    yield Service()


def check_esx_vsphere_sensors(params: Mapping[str, Any], section: _Section) -> CheckResult:
    mulitline = ["All sensors are in normal state", "Sensors operating normal are:"]
    mod_msg = " (Alert state has been modified by Check_MK rule)"

    for (
        name,
        _base_units,
        _current_reading,
        _sensor_type,
        _unit_modifier,
        _rate_units,
        health_key,
        health_label,
        health_summary,
    ) in section:
        sensor_state = _SENSOR_STATES.get(health_key.lower(), State.UNKNOWN)
        txt = f"{name}: {health_label} ({health_summary})"

        for entry in params["rules"]:
            if name.startswith(entry.get("name", "")):
                new_state = entry.get("states", {}).get(str(int(sensor_state)))  # str or int?
                if new_state is not None:
                    sensor_state = State(int(new_state))
                    txt += mod_msg
                    break
        if sensor_state is not State.OK or txt.endswith(mod_msg):
            yield Result(state=sensor_state, summary=txt)
            mulitline[:2] = "", "At least one sensor reported. Sensors readings are:"
        mulitline.append(txt)

    first, *remaining = mulitline
    if first:
        yield Result(state=State.OK, summary=first)
    if remaining:
        yield Result(state=State.OK, notice="\n".join(remaining))


def parse_esx_vsphere_sensors(string_table: StringTable) -> _Section:
    return string_table


agent_section_esx_vsphere_sensors = AgentSection(
    name="esx_vsphere_sensors",
    parse_function=parse_esx_vsphere_sensors,
)


check_plugin_esx_vsphere_sensors = CheckPlugin(
    name="esx_vsphere_sensors",
    service_name="Hardware Sensors",
    discovery_function=discover_esx_vsphere_sensors,
    check_function=check_esx_vsphere_sensors,
    check_ruleset_name="hostsystem_sensors",
    check_default_parameters={"rules": []},
)
