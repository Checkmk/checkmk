#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections import defaultdict
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
)


class Name(BaseModel, frozen=True):
    name: Optional[str] = None


class HostGroups(BaseModel, frozen=True):
    group: Optional[Name] = None
    members: Optional[list[Name]] = None


def parse_host_groups(string_table: StringTable) -> HostGroups | None:
    json_data = json.loads(string_table[0][0])
    if "items" not in json_data:
        return None
    grouped = defaultdict(list)

    for entry in json_data["items"]:
        group_name = entry.get("group", {}).get("name")
        member_name = entry.get("member", {}).get("name")

        if group_name and member_name:
            grouped[group_name].append(member_name)

    parsed = []
    for group_name, members in grouped.items():
        parsed.append(
            HostGroups(
                group=Name(name=group_name), members=[Name(name=m) for m in members]
            )
        )

    return parsed


agent_section_pure_storage_fa_host_groups = AgentSection(
    name="pure_storage_fa_host_groups",
    parse_function=parse_host_groups,
)


def discover_host_groups(section: list[HostGroups]) -> DiscoveryResult:
    for hgroup in section:
        yield Service(item=hgroup.group.name)


def check_host_groups(item: str, section: HostGroups) -> CheckResult:
    for hgroup in section:
        if item == hgroup.group.name:
            if hgroup.members:
                names = [m.name for m in hgroup.members if m.name]
                yield Result(state=State.OK, summary=f"Members: {', '.join(names)}")
            else:
                yield Result(state=State.OK, summary="No Members found")


check_plugin_pure_storage_fa_host_groups = CheckPlugin(
    name="pure_storage_fa_host_groups",
    service_name="Host Group %s",
    discovery_function=discover_host_groups,
    check_function=check_host_groups,
)
