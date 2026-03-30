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
    Metric,
    Result,
    Service,
    State,
)
from cmk.plugins.redfish.lib import RedfishAPIData


def discovery_redfish_power_consumption(section: RedfishAPIData) -> DiscoveryResult:
    for key in section:
        if section[key].get("PowerControl"):
            yield Service()
            return


def check_redfish_power_consumption(section: RedfishAPIData) -> CheckResult:
    powercontrol: list[Mapping[str, Any]] = []
    for key in section:
        if powercontrol_element := section[key].get("PowerControl"):
            powercontrol.extend(powercontrol_element)

    if not powercontrol:
        return

    result_submitted = False
    for element in powercontrol:
        summary_msg: list[str] = []
        mem_id = element.get("MemberId", "0")
        mem_name = element.get("Name", "PowerControl")
        system_wide_values: dict[str, Any] = {}
        for metric in ["PowerCapacityWatts", "PowerConsumedWatts"]:
            if (value := element.get(metric)) is not None:
                system_wide_values[metric] = value
                summary_msg.append(f"{metric} - {value} W")

        if summary_msg:
            result_submitted = True
            yield Result(state=State.OK, summary=f"{mem_name}: {' / '.join(summary_msg)}")

        if metrics := element.get("PowerMetrics"):
            for metric_name in [
                "AverageConsumedWatts",
                "MinConsumedWatts",
                "MaxConsumedWatts",
            ]:
                metric_value = metrics.get(metric_name)
                if metric_value is None:
                    continue
                maximum_value = system_wide_values.get("PowerCapacityWatts")
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

    if not result_submitted:
        yield Result(
            state=State.OK,
            summary="No power consumption data available.",
        )


check_plugin_redfish_power_consumption = CheckPlugin(
    name="redfish_power_consumption",
    service_name="Power consumption",
    sections=["redfish_power"],
    discovery_function=discovery_redfish_power_consumption,
    check_function=check_redfish_power_consumption,
)
