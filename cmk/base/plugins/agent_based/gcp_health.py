#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs

import datetime
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

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


# to lazy to type the full schema for incidents.
# https://status.cloud.google.com/incidents.schema.json
@dataclass(frozen=True)
class Incident:
    affected_products: Sequence[str]
    affected_location: Sequence[str]
    end: datetime.datetime | None
    description: str
    uri: str

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> "Incident":
        desc = data["external_desc"].replace("\n", "")
        products = [el["title"] for el in data["affected_products"]]
        locations = [el["id"] for el in data["most_recent_update"]["affected_locations"]]
        end = datetime.datetime.fromisoformat(data["end"]) if "end" in data else None
        uri = data["uri"]
        return cls(products, locations, end, desc, uri)

    def in_reference(self, smallest_accepted_time: datetime.datetime) -> bool:
        # checking the last known status might not work because it was not set to available.
        # for truly on going incidents the end marker is not existing.
        return self.end is None or smallest_accepted_time < self.end


@dataclass(frozen=True)
class Section:
    incidents: Sequence[Incident]


def parse(string_table: StringTable) -> Section:
    incidents = [Incident.from_json(el) for el in json.loads(string_table[0][0])]
    return Section(incidents)


register.agent_section(name="gcp_health", parse_function=parse)


def check(section: Section) -> CheckResult:
    smallest_accepted_time = datetime.datetime.now(datetime.UTC) - _IGNORE_ENTRIES_OLDER_THAN
    no_incident_found = True
    for incident in section.incidents:
        if incident.in_reference(smallest_accepted_time):
            yield Result(
                state=State.CRIT,
                summary=incident.description,
                details=f"Products: {', '.join(incident.affected_products)} \n Locations: {', '.join(incident.affected_location)}, \n {BASE_URL}{incident.uri}",
            )
            no_incident_found = False
    if no_incident_found:
        yield Result(
            state=State.OK,
            summary=f"No known incident in the past {_DISPLAYED_AGE} {BASE_URL}",
        )


def discovery(section: Section) -> DiscoveryResult:
    yield Service()


register.check_plugin(
    name="gcp_health",
    service_name="GCP Health",
    discovery_function=discovery,
    check_function=check,
)
