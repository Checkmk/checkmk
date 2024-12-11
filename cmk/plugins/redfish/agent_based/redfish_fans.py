#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-

# (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>

# License: GNU General Public License v2

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
    RedfishAPIData,
    process_redfish_perfdata,
    redfish_health_state,
)


def _fan_item_name(data):
    fan_name = data.get("Name", data.get("FanName", None))
    if fan_name:
        if fan_name.startswith("Fan"):
            fan_name = fan_name.lstrip("Fan").strip()
        return fan_name
    return None


def discovery_redfish_fans(section: RedfishAPIData) -> DiscoveryResult:
    """Discover single fans"""
    for key in section.keys():
        fans = section[key].get("Fans", None)
        if not fans:
            continue
        for fan in fans:
            if fan.get("Status", {}).get("State") == "Absent":
                continue
            fan_name = _fan_item_name(fan)
            if fan_name:
                yield Service(item=fan_name)


def check_redfish_fans(item: str, section: RedfishAPIData) -> CheckResult:
    """Check single fan state"""
    fan = None
    for key in section.keys():
        fans = section[key].get("Fans", None)
        if fans is None:
            return

        for fan_data in fans:
            fan_name = _fan_item_name(fan_data)
            if fan_name == item:
                fan = fan_data
                break
        if fan:
            break

    if not fan:
        return

    perfdata = process_redfish_perfdata(fan)
    units = fan.get("ReadingUnits", None)

    if not perfdata:
        yield Result(state=State(0), summary="No performance data found")
    elif units == "Percent":
        yield from check_levels(
            value=perfdata.value,
            levels_upper=perfdata.levels_upper,
            levels_lower=perfdata.levels_lower,
            metric_name="perc",
            label="Speed",
            render_func=lambda v: f"{v:.1f}%",
            boundaries=(0, 100),
        )
    elif units == "RPM":
        yield from check_levels(
            value=perfdata.value,
            levels_upper=perfdata.levels_upper,
            levels_lower=perfdata.levels_lower,
            metric_name="fan",
            label="Speed",
            render_func=lambda v: f"{v:.1f} rpm",
            boundaries=perfdata.boundaries,
        )
    else:
        yield from check_levels(
            value=perfdata.value,
            levels_upper=perfdata.levels_upper,
            levels_lower=perfdata.levels_lower,
            metric_name="fan",
            label="Speed",
            render_func=lambda v: f"{v:.1f} rpm",
            boundaries=perfdata.boundaries,
        )
        yield Result(state=State(0), summary="No unit found assume RPM!")

    dev_state, dev_msg = redfish_health_state(fan.get("Status", {}))

    yield Result(state=State(dev_state), notice=dev_msg)


check_plugin_redfish_fans = CheckPlugin(
    name="redfish_fans",
    service_name="Fan %s",
    sections=["redfish_thermal"],
    discovery_function=discovery_redfish_fans,
    check_function=check_redfish_fans,
)
