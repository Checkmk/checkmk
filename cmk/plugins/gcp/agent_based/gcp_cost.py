#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs
import datetime
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    StringTable,
)

ProjectId = str


class Cost(BaseModel):
    model_config = ConfigDict(frozen=True)

    month: datetime.datetime
    amount: float
    currency: str
    project: str

    @field_validator("month", mode="before")
    @classmethod
    def parse_month(cls, value: str) -> datetime.datetime:
        return datetime.datetime.strptime(value, "%Y%m")

    def to_details(self) -> str:
        return f"{self.date()}: {self.amount:.2f} {self.currency}"

    def date(self) -> str:
        return self.month.strftime("%B %Y")


@dataclass(frozen=True)
class ProjectCost:
    project: str
    current_month: Cost


Section = Mapping[ProjectId, ProjectCost]


def parse(string_table: StringTable) -> Section:
    query_month = datetime.datetime.strptime(json.loads(string_table[0][0])["query_month"], "%Y%m")

    section = {}
    for row in [json.loads(line[0]) for line in string_table[1:]]:
        cost = Cost.model_validate(row)
        if cost.month != query_month:
            # just to make sure, query should only return values of that month
            continue

        project = ProjectCost(
            cost.project,
            current_month=cost,
        )
        section[row["id"]] = project

    return section


agent_section_gcp_cost = AgentSection(name="gcp_cost", parse_function=parse)


def discover(section: Section) -> DiscoveryResult:
    for project in section:
        yield Service(item=project)


def check(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if item not in section:
        return
    project_costs = section[item]
    current_month = project_costs.current_month

    yield from check_levels(
        value=current_month.amount,
        levels_upper=params["levels"],
        metric_name="gcp_cost_per_month",
        render_func=lambda x: f"{x:.2f} {current_month.currency}",
        label=current_month.date(),
    )


check_plugin_gcp_cost = CheckPlugin(
    name="gcp_cost",
    service_name="Costs project %s",
    discovery_function=discover,
    check_function=check,
    check_ruleset_name="gcp_cost",
    check_default_parameters={"levels": None},
)
