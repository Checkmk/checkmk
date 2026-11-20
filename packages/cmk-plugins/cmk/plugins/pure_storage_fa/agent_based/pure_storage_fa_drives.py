#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Optional

from pydantic import BaseModel

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
    check_levels,
    Metric,
)


class Drives(BaseModel, frozen=True):
    type: Optional[str] = None
    name: Optional[str] = None
    protocol: Optional[str] = None
    status: Optional[str] = None
    capacity: Optional[int] = None
    capacity_installed: Optional[int] = None
    details: Optional[str] = None


def parse_drives(string_table: StringTable) -> Drives | None:
    json_data = json.loads(string_table[0][0])
    if "items" not in json_data:
        return None
    parsed = []
    for drive in json_data["items"]:
        parsed.append(Drives(**drive))

    return parsed


agent_section_pure_storage_fa_drives = AgentSection(
    name="pure_storage_fa_drives",
    parse_function=parse_drives,
)


def discover_drives(section: list[Drives]) -> DiscoveryResult:
    for drive in section:
        yield Service(
            item=drive.name, parameters=dict({"discovered_state": drive.status})
        )


def check_drives(item, params, section: Drives) -> CheckResult:
    if section == []:
        yield Result(state=State.CRIT, summary="No Drives found!")
    for drive in section:
        if item == drive.name:
            if (
                drive.status in params["discovered_state"]
                or drive.status in params["state"]
            ):
                yield Result(
                    state=State.OK,
                    summary=f"{drive.type} {item} is {drive.status}",
                )
                yield from check_levels(
                    drive.capacity / 1000000000,
                    metric_name="pure_storage_fa_drive_capacity",
                    render_func=lambda v: (
                        f"Capacity: {v} GB,\nProtocol: {drive.protocol}"
                    ),
                    notice_only=True,
                )
            else:
                yield Metric("pure_storage_fa_drive_capacity", drive.capacity)
                yield Result(
                    state=State.CRIT, summary=f"{drive.name} is {drive.status}"
                )


check_plugin_pure_storage_fa_drives = CheckPlugin(
    name="pure_storage_fa_drives",
    service_name="Drive %s",
    discovery_function=discover_drives,
    check_function=check_drives,
    check_default_parameters={"state": "healthy"},
)
