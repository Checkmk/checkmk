#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)

from .lib import parse_hp_msa, Section

# <<<hp_msa_fan>>>
# fan 1 durable-id fan_1.1
# fan 1 name Fan Loc:left-PSU 1
# fan 1 location Enclosure 1 - Left
# fan 1 status Up
# fan 1 status-numeric 0
# fan 1 speed 3760
# fan 1 position Left
# fan 1 position-numeric 0
# fan 1 serial-number
# fan 1 fw-revision
# fan 1 hw-revision
# fan 1 health OK
# fan 1 health-numeric 0
# fan 1 health-reason
# fan 1 health-recommendation
# fan 2 durable-id fan_1.2
# fan 2 name Fan Loc:right-PSU 2
# fan 2 location Enclosure 1 - Right
# fan 2 status Up
# fan 2 status-numeric 0
# fan 2 speed 3880
# fan 2 position Right
# fan 2 position-numeric 1
# fan 2 serial-number
# fan 2 fw-revision
# fan 2 hw-revision
# fan 2 health OK
# fan 2 health-numeric 0
# fan 2 health-reason
# fan 2 health-recommendation

hp_msa_state_numeric_map = {
    "0": (State.OK, "up"),
    "1": (State.CRIT, "error"),
    "2": (State.WARN, "off"),
    "3": (State.UNKNOWN, "missing"),
}

hp_msa_health_state_numeric_map = {
    "0": (State.OK, "OK"),
    "1": (State.WARN, "degraded"),
    "2": (State.CRIT, "fault"),
    "3": (State.CRIT, "N/A"),
    "4": (State.UNKNOWN, "unknown"),
}


def discover_hp_msa_fan(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_hp_msa_fan(item: str, section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        return

    fan_speed = int(data["speed"])
    fan_state, fan_state_readable = hp_msa_state_numeric_map[data["status-numeric"]]
    fan_health_state, fan_health_state_readable = hp_msa_health_state_numeric_map[
        data["health-numeric"]
    ]
    fan_health_reason = data.get("health-reason", "")

    yield Result(state=fan_state, summary=f"Status: {fan_state_readable}, speed: {fan_speed} RPM")

    if fan_health_state is not State.OK and fan_health_reason:
        yield Result(
            state=fan_health_state,
            summary=f"health: {fan_health_state_readable} ({fan_health_reason})",
        )


agent_section_hp_msa_fan = AgentSection(
    name="hp_msa_fan",
    parse_function=parse_hp_msa,
)

check_plugin_hp_msa_fan = CheckPlugin(
    name="hp_msa_fan",
    service_name="Fan %s",
    discovery_function=discover_hp_msa_fan,
    check_function=check_hp_msa_fan,
)
