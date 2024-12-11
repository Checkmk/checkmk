#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.redfish.lib import (
    process_redfish_perfdata,
    redfish_health_state,
    RedfishAPIData,
)


def discovery_redfish_voltage(section: RedfishAPIData) -> DiscoveryResult:
    for key in section.keys():
        data = section[key].get("Voltages", None)
        if not data:
            continue
        for entry in data:
            if not entry.get("ReadingVolts"):
                continue
            if not entry["Name"]:
                continue
            yield Service(item=entry["Name"])


def check_redfish_voltage(item: str, section: RedfishAPIData) -> CheckResult:
    """Check single Voltage"""
    voltage = None
    for key in section.keys():
        voltages = section[key].get("Voltages", None)
        if voltages is None:
            return

        for voltage_data in voltages:
            if voltage_data.get("Name") == item:
                voltage = voltage_data
                break
        if voltage:
            break

    if not voltage:
        return

    perfdata = process_redfish_perfdata(voltage)

    volt_msg = (
        f"Location: {voltage.get('PhysicalContext')}, " f"SensorNr: {voltage.get('SensorNumber')}"
    )
    yield Result(state=State(0), summary=volt_msg)

    if perfdata and perfdata.value is not None:
        yield from check_levels(
            value=perfdata.value,
            levels_upper=perfdata.levels_upper,
            levels_lower=perfdata.levels_lower,
            metric_name="voltage",
            label="Value",
            render_func=lambda v: f"{v:.1f} V",
            boundaries=perfdata.boundaries,
        )

    dev_state, dev_msg = redfish_health_state(voltage.get("Status", {}))
    yield Result(state=State(dev_state), notice=dev_msg)


check_plugin_redfish_voltage = CheckPlugin(
    name="redfish_voltage",
    service_name="Voltage %s",
    sections=["redfish_power"],
    discovery_function=discovery_redfish_voltage,
    check_function=check_redfish_voltage,
)
