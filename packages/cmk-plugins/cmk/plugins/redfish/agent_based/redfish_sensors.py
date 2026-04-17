#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""check single redfish sensor state"""

from collections.abc import Callable

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    render,
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
    Levels,
    parse_redfish_multiple,
    Perfdata,
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


def _dev_levels(levels: Levels | None) -> tuple[float, float] | None:
    """Extract device-level thresholds for check_temperature/check_humidity."""
    if levels and len(levels) > 1:
        return levels[1]
    return None


def _check_sensor_levels(
    perfdata: Perfdata,
    *,
    metric_name: str,
    label: str,
    render_func: Callable[[float], str],
    boundaries: tuple[float | None, float | None] | None = None,
) -> CheckResult:
    """Yield check_levels result for a generic sensor reading."""
    yield from check_levels(
        value=perfdata.value,
        levels_upper=perfdata.levels_upper,
        levels_lower=perfdata.levels_lower,
        metric_name=metric_name,
        label=label,
        render_func=render_func,
        boundaries=boundaries if boundaries is not None else perfdata.boundaries,
    )


def check_redfish_sensors(item: str, params: TempParamDict, section: RedfishAPIData) -> CheckResult:
    """Check single sensor state"""
    data = section.get(item)
    if data is None:
        return

    perfdata = process_redfish_perfdata(data)
    if perfdata:
        match data.get("ReadingType"):
            case "Temperature":
                yield from check_temperature(
                    perfdata.value,
                    params,
                    unique_name=f"redfish.temp.{item}",
                    value_store=get_value_store(),
                    dev_levels=_dev_levels(perfdata.levels_upper),
                    dev_levels_lower=_dev_levels(perfdata.levels_lower),
                )
            case "Humidity":
                yield from check_humidity(
                    humidity=perfdata.value,
                    params={
                        "levels": _dev_levels(perfdata.levels_upper),
                        "levels_lower": _dev_levels(perfdata.levels_lower),
                    },
                )
            case "Rotational":
                if data.get("ReadingUnits") == "Percent":
                    yield from _check_sensor_levels(
                        perfdata,
                        metric_name="perc",
                        label="Speed",
                        render_func=render.percent,
                        boundaries=(0, 100),
                    )
                else:
                    yield from _check_sensor_levels(
                        perfdata,
                        metric_name="fan",
                        label="Speed",
                        render_func=lambda v: f"{v:.0f} rpm",
                    )
            case "Voltage":
                yield from _check_sensor_levels(
                    perfdata,
                    metric_name="voltage",
                    label="Voltage",
                    render_func=lambda v: f"{v:.1f} V",
                )
            case "Current":
                yield from _check_sensor_levels(
                    perfdata,
                    metric_name="current",
                    label="Current",
                    render_func=lambda v: f"{v:.1f} A",
                )
            case "Power":
                yield from _check_sensor_levels(
                    perfdata, metric_name="power", label="Power", render_func=lambda v: f"{v:.1f} W"
                )
            case "Frequency":
                yield from _check_sensor_levels(
                    perfdata,
                    metric_name="frequency",
                    label="Frequency",
                    render_func=lambda v: f"{v:.1f} Hz",
                )
            case "Percent":
                yield from _check_sensor_levels(
                    perfdata,
                    metric_name="perc",
                    label="Usage",
                    render_func=render.percent,
                    boundaries=(0, 100),
                )
            case other:
                yield Result(
                    state=State(0),
                    summary=f"{other or 'Unknown'} reading: {perfdata.value}",
                )
    else:
        yield Result(state=State(0), summary="No reading data available")

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
