#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

# Pydantic requires the property to be under computed_field to work.
# mypy: disable-error-code="prop-decorator"

import json
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, computed_field

from cmk.agent_based.v2 import (
    AgentSection,
    InventoryPlugin,
    InventoryResult,
    StringTable,
    TableRow,
)

type Section = Sequence[Organization]


class Api(BaseModel, frozen=True):
    enabled: bool


class Licensing(BaseModel, frozen=True):
    model: str


class Region(BaseModel, frozen=True):
    name: str


class Cloud(BaseModel, frozen=True):
    region: Region


class Organization(BaseModel, frozen=True):
    id: str
    name: str
    url: str
    api: Api
    licensing: Licensing
    cloud: Cloud

    @computed_field
    @property
    def api_status(self) -> Literal["enabled", "disabled"]:
        return "enabled" if self.api.enabled else "disabled"


def parse_meraki_organizations(string_table: StringTable) -> Section:
    match string_table:
        case [[payload]] if payload:
            return [Organization.model_validate(item) for item in json.loads(payload)]
        case _:
            return []


agent_section_cisco_meraki_org_organisations = AgentSection(
    name="cisco_meraki_org_organisations",
    parsed_section_name="cisco_meraki_org_organisations",
    parse_function=parse_meraki_organizations,
)


def inventory_meraki_organizations(section: Section) -> InventoryResult:
    for organization in section:
        yield TableRow(
            path=["software", "applications", "cisco_meraki", "organisations"],
            key_columns={"org_id": organization.id},
            inventory_columns={
                "org_name": organization.name,
                "url": organization.url,
                "api": organization.api_status,
                "licensing": organization.licensing.model,
                "cloud": organization.cloud.region.name,
            },
        )


inventory_plugin_cisco_meraki_org_organisations = InventoryPlugin(
    name="cisco_meraki_org_organisations",
    sections=["cisco_meraki_org_organisations"],
    inventory_function=inventory_meraki_organizations,
)
