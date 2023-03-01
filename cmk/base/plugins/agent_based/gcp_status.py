#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs

import datetime
from collections.abc import Sequence

import pydantic

from cmk.utils import gcp_constants  # pylint: disable=cmk-module-layer-violation

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, render, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)

BASE_URL = "https://status.cloud.google.com/"
_IGNORE_ENTRIES_OLDER_THAN = datetime.timedelta(days=3)  # Product-Management decision
_DISPLAYED_AGE = render.timespan(_IGNORE_ENTRIES_OLDER_THAN.total_seconds()).removesuffix(
    " 0 hours"
)


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
    end: datetime.datetime | None
    external_desc: str
    uri: str

    def region_ids(self) -> list[str]:
        return [l.id_ for l in self.currently_affected_locations]

    def in_reference(self, smallest_accepted_time: datetime.datetime) -> bool:
        # checking the last known status might not work because it was not set to available.
        # for truly on going incidents the end marker is not existing.
        return self.end is None or smallest_accepted_time < self.end


class Section(pydantic.BaseModel):
    discovery_param: DiscoveryParam
    # health_info corresponds to gcp json scheme provided here:
    # https://status.cloud.google.com/incidents.schema.json
    # Some fields have been omitted.
    health_info: Sequence[Incident]


def parse(string_table: StringTable) -> Section:
    return Section.parse_raw(string_table[0][0])


register.agent_section(name="gcp_status", parse_function=parse)


def check(item: str, section: Section) -> CheckResult:
    smallest_accepted_time = datetime.datetime.now(datetime.UTC) - _IGNORE_ENTRIES_OLDER_THAN
    relevant_incidents = [
        incident
        for incident in section.health_info
        if incident.in_reference(smallest_accepted_time) and item in incident.region_ids()
    ]
    for incident in relevant_incidents:
        product_description = "Products: " + ", ".join(p.title for p in incident.affected_products)
        location_description = "Locations: " + ", ".join(incident.region_ids())
        yield Result(
            state=State.CRIT,
            summary=incident.external_desc.replace("\n", ""),
            details=f"{product_description} \n {location_description} \n {BASE_URL}{incident.uri}",
        )
    if not relevant_incidents:
        yield Result(
            state=State.OK,
            summary=f"No known incident in the past {_DISPLAYED_AGE} {BASE_URL}",
        )


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
