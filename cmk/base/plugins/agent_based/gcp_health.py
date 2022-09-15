#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs

import datetime
import json
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Pattern, Sequence

from cmk.base.plugins.agent_based.agent_based_api.v1 import regex, register, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)

BASE_URL = "https://status.cloud.google.com/"


@dataclass(frozen=True)
class Interval:
    start: datetime.datetime
    end: datetime.datetime

    def __post_init__(self) -> None:
        if self.end and self.start > self.end:
            raise ValueError(
                f"Expect that start {self.start} is always earlier than end {self.end}"
            )


# to lazy to type the full schema for incidents.
# https://status.cloud.google.com/incidents.schema.json
@dataclass(frozen=True)
class Incident:
    affected_products: Sequence[str]
    affected_location: Sequence[str]
    begin: datetime.datetime
    end: Optional[datetime.datetime]
    description: str
    is_on_going: bool
    uri: str

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> "Incident":
        desc = data["external_desc"].replace("\n", "")
        products = [el["title"] for el in data["affected_products"]]
        locations = [el["id"] for el in data["most_recent_update"]["affected_locations"]]
        begin = datetime.datetime.fromisoformat(data["begin"])
        end = datetime.datetime.fromisoformat(data["end"]) if "end" in data else None
        # checking the last known status might not work because it was not set to available.
        # for truly on going incidents the end marker is not existing.
        on_going = end is None
        uri = data["uri"]
        return cls(products, locations, begin, end, desc, on_going, uri)

    # ignore pathological cases occuring when used incorrectly. I.e. the agent is run with a date parameter in the past.
    # That could lead to finding an incident that has started in our refernce window and concluded after it.
    def in_reference(self, ref: Interval) -> bool:
        if self.end is None:
            raise ValueError("Do not call in_refernce on open incident")
        if ref.start < self.end and self.end < ref.end:
            return True
        return False


@dataclass(frozen=True)
class Section:
    date: datetime.datetime
    incidents: Sequence[Incident]


def parse(string_table: StringTable) -> Section:
    date_str = json.loads(string_table[0][0])["date"]
    date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    # needed for comparison in equal timezone later. Since we only care about a day this is fine.
    date = date.replace(tzinfo=datetime.timezone.utc)
    incidents = [Incident.from_json(el) for el in json.loads(string_table[1][0])]
    return Section(date, incidents)


register.agent_section(name="gcp_health", parse_function=parse)


def report_incident(
    incident: Incident,
    reference_interval: Interval,
    product_regex: Sequence[Pattern[str]],
    region_regex: Sequence[Pattern[str]],
) -> bool:
    if len(product_regex) != 0:
        if not any(prex.search(p) for p in incident.affected_products for prex in product_regex):
            return False
    if len(region_regex) != 0:
        if not (
            any(rrex.search(r) for r in incident.affected_location for rrex in region_regex)
            or "global" in incident.affected_location
        ):
            return False
    return incident.is_on_going or incident.in_reference(reference_interval)


def check(params: Mapping[str, Any], section: Section) -> CheckResult:
    reference_interval = Interval(
        section.date - datetime.timedelta(days=params["time_window"]), section.date
    )
    product_regex = [regex(el) for el in params["product_filter"]]
    region_regex = [regex(el) for el in params["region_filter"]]
    no_incident_found = True
    for incident in section.incidents:
        if report_incident(incident, reference_interval, product_regex, region_regex):
            yield Result(
                state=State.CRIT if incident.is_on_going else State.WARN,
                summary=incident.description,
                details=f"Products: {', '.join(incident.affected_products)} \n Locations: {', '.join(incident.affected_location)}, \n {BASE_URL}{incident.uri}",
            )
            no_incident_found = False
    if no_incident_found:
        yield Result(
            state=State.OK,
            summary=f"No known incident in the past {params['time_window']} days {BASE_URL}",
        )


def discovery(section: Section) -> DiscoveryResult:
    yield Service()


register.check_plugin(
    name="gcp_health",
    service_name="GCP Status",
    discovery_function=discovery,
    check_function=check,
    check_ruleset_name="gcp_health",
    check_default_parameters={"time_window": 2, "region_filter": [], "product_filter": []},
)
