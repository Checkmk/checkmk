#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check environment metrics: aggregate power and fan data (modern Redfish resource model)"""

import re

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
)
from cmk.plugins.redfish.lib import (
    parse_redfish_multiple,
    RedfishAPIData,
)

agent_section_redfish_environmentmetrics = AgentSection(
    name="redfish_environmentmetrics",
    parse_function=parse_redfish_multiple,
    parsed_section_name="redfish_environmentmetrics",
)


def _sanitize_metric_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", name)


def discovery_redfish_environmentmetrics(section: RedfishAPIData) -> DiscoveryResult:
    for key in section:
        yield Service(item=key)


def check_redfish_environmentmetrics(item: str, section: RedfishAPIData) -> CheckResult:
    data = section.get(item)
    if data is None:
        return

    power_watts = data.get("PowerWatts", {})
    if isinstance(power_watts, dict) and (reading := power_watts.get("Reading")) is not None:
        yield Metric("power", float(reading))
        yield Result(state=State.OK, summary=f"Power consumption: {reading:.0f} W")

    for idx, fan_entry in enumerate(data.get("FanSpeedsPercent", [])):
        if isinstance(fan_entry, dict) and (reading := fan_entry.get("Reading")) is not None:
            name = _sanitize_metric_name(fan_entry.get("DeviceName", f"Fan{idx}"))
            yield Metric(f"perc_{name}", float(reading))

    for idx, temp_entry in enumerate(data.get("TemperatureCelsius", [])):
        if isinstance(temp_entry, dict) and (reading := temp_entry.get("Reading")) is not None:
            name = _sanitize_metric_name(temp_entry.get("DeviceName", f"Temp{idx}"))
            yield Metric(f"temp_{name}", float(reading))


check_plugin_redfish_environmentmetrics = CheckPlugin(
    name="redfish_environmentmetrics",
    service_name="Environment %s",
    sections=["redfish_environmentmetrics"],
    discovery_function=discovery_redfish_environmentmetrics,
    check_function=check_redfish_environmentmetrics,
)
