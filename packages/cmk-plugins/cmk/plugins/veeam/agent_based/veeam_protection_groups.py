#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
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


class ProtectionGroupType(StrEnum):
    MANUALLY_ADDED = "ManuallyAdded"
    UNMANAGED = "Unmanaged"
    INDIVIDUAL_COMPUTERS = "IndividualComputers"
    AD_OBJECTS = "ADObjects"
    CSV_FILE = "CSVFile"
    PRE_INSTALLED_AGENTS = "PreInstalledAgents"
    CLOUD_MACHINES = "CloudMachines"
    MONGO_DB = "MongoDB"


@dataclass(frozen=True, kw_only=True)
class VeeamProtectionGroup:
    """Mirrors the VBR REST API's ProtectionGroupModel
    (GET /api/v1/agents/protectionGroups)."""

    type: ProtectionGroupType | str
    description: str
    is_disabled: bool
    computer_count: int | None


Section = Mapping[str, VeeamProtectionGroup]


class CheckParameters(TypedDict):
    disabled_state: int


DEFAULT_PARAMETERS = CheckParameters(disabled_state=State.OK.value)


def parse_veeam_protection_groups(string_table: StringTable) -> Section:
    section: dict[str, VeeamProtectionGroup] = {}
    for line in string_table:
        group_dict = json.loads(line[0])
        section[group_dict["name"]] = VeeamProtectionGroup(
            type=_parse_type(group_dict["type"]),
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


def _parse_type(raw_type: str) -> ProtectionGroupType | str:
    try:
        return ProtectionGroupType(raw_type)
    except ValueError:
        return raw_type


def _known_type_display_name(type_: ProtectionGroupType) -> str:
    match type_:
        case ProtectionGroupType.MANUALLY_ADDED:
            return "Manually added"
        case ProtectionGroupType.UNMANAGED:
            return "Unmanaged"
        case ProtectionGroupType.INDIVIDUAL_COMPUTERS:
            return "Individual computers"
        case ProtectionGroupType.AD_OBJECTS:
            return "Active Directory objects"
        case ProtectionGroupType.CSV_FILE:
            return "CSV file"
        case ProtectionGroupType.PRE_INSTALLED_AGENTS:
            return "Pre-installed agents"
        case ProtectionGroupType.CLOUD_MACHINES:
            return "Cloud machines"
        case ProtectionGroupType.MONGO_DB:
            return "MongoDB"


def _type_display_name(type_: ProtectionGroupType | str) -> str:
    return _known_type_display_name(type_) if isinstance(type_, ProtectionGroupType) else type_


def check_veeam_protection_groups(
    item: str, params: CheckParameters, section: Section
) -> CheckResult:
    if (group := section.get(item)) is None:
        return

    fields = [f"Type: {_type_display_name(group.type)}"]
    if group.computer_count is not None:
        fields.append(f"Configured computers: {group.computer_count}")
    fields.append(f"State: {'Disabled' if group.is_disabled else 'Enabled'}")
    yield Result(
        state=State(params["disabled_state"]) if group.is_disabled else State.OK,
        summary=", ".join(fields),
    )

    if group.computer_count is None:
        yield Result(state=State.OK, notice="Configured computers: not listed for this group type")

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
    service_name="Veeam Protection group %s",
    discovery_function=discovery_veeam_protection_groups,
    check_function=check_veeam_protection_groups,
    check_ruleset_name="veeam_protection_groups",
    check_default_parameters=DEFAULT_PARAMETERS,
)
