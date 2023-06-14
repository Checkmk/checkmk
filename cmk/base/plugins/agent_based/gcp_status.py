#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs

import dataclasses
from collections.abc import Mapping, Sequence

import pydantic

from cmk.utils import gcp_constants  # pylint: disable=cmk-module-layer-violation

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)

BASE_URL = "https://status.cloud.google.com/"
_NO_ISSUES = Result(state=State.OK, summary=f"No known issues. Details: {BASE_URL}")


class DiscoveryParam(pydantic.BaseModel):
    """Config scheme: discovery for gcp_status.

    This is used by the discovery function of gcp_status. Configuration is passed in the special
    agent rule, so the user has a all-in-one view.
    """

    regions: list[str]


class AffectedProduct(pydantic.BaseModel):
    title: str


class AffectedLocation(pydantic.BaseModel):
    id_: str = pydantic.Field(..., alias="id")


class Incident(pydantic.BaseModel):
    affected_products: Sequence[AffectedProduct]
    currently_affected_locations: Sequence[AffectedLocation]
    external_desc: str
    uri: str


class AgentOutput(pydantic.BaseModel):
    discovery_param: DiscoveryParam
    # health_info corresponds to gcp json scheme provided here:
    # https://status.cloud.google.com/incidents.schema.json
    # Some fields have been omitted.
    health_info: Sequence[Incident]


@dataclasses.dataclass
class Section:
    discovery_param: DiscoveryParam
    data: Mapping[str, Sequence[Incident]]


def parse(string_table: StringTable) -> Section:
    output = AgentOutput.parse_raw(string_table[0][0])
    data: dict[str, list[Incident]] = {}
    for incident in output.health_info:
        for location in incident.currently_affected_locations:
            data.setdefault(gcp_constants.RegionMap[location.id_], []).append(incident)
    return Section(discovery_param=output.discovery_param, data=data)


register.agent_section(name="gcp_status", parse_function=parse)


def check(item: str, section: Section) -> CheckResult:
    relevant_incidents = section.data.get(item, [])
    for incident in relevant_incidents:
        product_description = "Products: " + ", ".join(p.title for p in incident.affected_products)
        yield Result(
            state=State.CRIT,
            summary=incident.external_desc.replace("\n", ""),
            details=f"{product_description} \n {BASE_URL}{incident.uri}",
        )
    if not relevant_incidents:
        yield _NO_ISSUES


def discovery(section: Section) -> DiscoveryResult:
    yield Service(item="Global")
    for region in section.discovery_param.regions:
        yield Service(item=gcp_constants.RegionMap[region])


register.check_plugin(
    name="gcp_status",
    service_name="GCP Status %s",
    discovery_function=discovery,
    check_function=check,
)
