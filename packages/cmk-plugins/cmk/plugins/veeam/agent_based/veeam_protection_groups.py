#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypedDict

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


@dataclass(frozen=True, kw_only=True)
class VeeamProtectionGroup:
    """Mirrors the VBR REST API's ProtectionGroupModel
    (GET /api/v1/agents/protectionGroups)."""

    type: str
    description: str
    is_disabled: bool
    computer_count: int | None


Section = Mapping[str, VeeamProtectionGroup]


class CheckParameters(TypedDict):
    disabled_state: int


def parse_veeam_protection_groups(string_table: StringTable) -> Section:
    section: dict[str, VeeamProtectionGroup] = {}
    for line in string_table:
        group_dict = json.loads(line[0])
        section[group_dict["name"]] = VeeamProtectionGroup(
            type=group_dict["type"],
            description=group_dict["description"],
            is_disabled=group_dict["isDisabled"],
            # Only the IndividualComputers and ManuallyAdded models have this field.
            computer_count=None
            if (computers := group_dict.get("computers")) is None
            else len(computers),
        )
    return section


def discovery_veeam_protection_groups(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def _type_display_name(raw_type: str) -> str:
    # TODO(CMK-40441): type the EProtectionGroupType values as a Literal/StrEnum.
    match raw_type:
        case "ManuallyAdded":
            return "Manually added"
        case "Unmanaged":
            return "Unmanaged"
        case "IndividualComputers":
            return "Individual computers"
        case "ADObjects":
            return "Active Directory objects"
        case "CSVFile":
            return "CSV file"
        case "PreInstalledAgents":
            return "Pre-installed agents"
        case "CloudMachines":
            return "Cloud machines"
        case "MongoDB":
            return "MongoDB"
        case _:
            return raw_type


def check_veeam_protection_groups(
    item: str, params: CheckParameters, section: Section
) -> CheckResult:
    if (group := section.get(item)) is None:
        return

    summary = _type_display_name(group.type)
    if (count := group.computer_count) is not None:
        summary += f", {count} configured computer{'' if count == 1 else 's'}"
    if group.is_disabled:
        yield Result(state=State(params["disabled_state"]), summary=f"{summary}, Disabled")
    else:
        yield Result(state=State.OK, summary=summary)

    yield Result(
        state=State.OK,
        notice=f"Description: {group.description}" if group.description else "Description: none",
    )


agent_section_veeam_protection_groups = AgentSection(
    name="veeam_protection_groups",
    parse_function=parse_veeam_protection_groups,
)

check_plugin_veeam_protection_groups = CheckPlugin(
    name="veeam_protection_groups",
    service_name="Protection group %s",
    discovery_function=discovery_veeam_protection_groups,
    check_function=check_veeam_protection_groups,
    check_ruleset_name="veeam_protection_groups",
    check_default_parameters=CheckParameters(disabled_state=1),
)
