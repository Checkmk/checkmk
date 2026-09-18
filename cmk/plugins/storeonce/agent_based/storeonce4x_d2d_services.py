#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from dataclasses import dataclass

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


@dataclass(frozen=True)
class D2DService:
    health_level: str
    health: str
    subsystem_state: str


Section = Mapping[str, D2DService]

_HEALTH_MAP = {"OK": State.OK, "WARNING": State.WARN, "CRITICAL": State.CRIT}


def parse_storeonce4x_d2d_services(string_table: StringTable) -> Section:
    return {
        service_name: D2DService(
            health_level=service_data["healthLevelString"],
            health=service_data["healthString"],
            subsystem_state=service_data["subsystemState"],
        )
        for service_name, service_data in json.loads(string_table[0][0])["services"].items()
    }


agent_section_storeonce4x_d2d_services = AgentSection(
    name="storeonce4x_d2d_services",
    parse_function=parse_storeonce4x_d2d_services,
)


def discover_storeonce4x_d2d_services(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_storeonce4x_d2d_services(section: Section) -> CheckResult:
    for service_name, service in section.items():
        yield Result(
            state=_HEALTH_MAP.get(service.health_level, State.UNKNOWN),
            summary=f"{service_name}: {service.health} ({service.subsystem_state})",
        )


check_plugin_storeonce4x_d2d_services = CheckPlugin(
    name="storeonce4x_d2d_services",
    service_name="D2D Services",
    discovery_function=discover_storeonce4x_d2d_services,
    check_function=check_storeonce4x_d2d_services,
)
