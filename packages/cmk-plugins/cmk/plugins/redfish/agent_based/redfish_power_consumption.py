#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
)
from cmk.plugins.redfish.lib import RedfishAPIData


def discovery_redfish_power_consumption(section: RedfishAPIData) -> DiscoveryResult:
    for key in section:
        power_control = section[key].get("PowerControl")
        if not power_control:
            continue
        for entry in power_control:
            if entry.get("PowerConsumedWatts") is not None or entry.get("PowerMetrics"):
                mem_id = entry.get("MemberId", "0")
                yield Service(item=mem_id)


def check_redfish_power_consumption(item: str, section: RedfishAPIData) -> CheckResult:
    for key in section:
        power_control = section[key].get("PowerControl")
        if not power_control:
            continue
        for entry in power_control:
            mem_id = entry.get("MemberId", "0")
            if mem_id != item:
                continue

            system_wide_values = entry
            if (consumed := system_wide_values.get("PowerConsumedWatts")) is not None:
                yield Result(state=State.OK, summary=f"Current power: {consumed} W")

            metrics = system_wide_values.get("PowerMetrics", {})
            maximum_value = system_wide_values.get("PowerCapacityWatts")

            for metric_name in [
                "AverageConsumedWatts",
                "MinConsumedWatts",
                "MaxConsumedWatts",
            ]:
                metric_value = metrics.get(metric_name)
                if metric_value is None:
                    continue
                if maximum_value:
                    yield Metric(
                        name=f"{metric_name.lower()}_{mem_id}",
                        value=float(metric_value),
                        boundaries=(0, float(maximum_value)),
                    )
                else:
                    yield Metric(
                        name=f"{metric_name.lower()}_{mem_id}",
                        value=float(metric_value),
                    )

            return


check_plugin_redfish_power_consumption = CheckPlugin(
    name="redfish_power_consumption",
    service_name="Power consumption %s",
    sections=["redfish_power"],
    discovery_function=discovery_redfish_power_consumption,
    check_function=check_redfish_power_consumption,
)
