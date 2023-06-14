#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs
import datetime
import json
from collections.abc import Mapping
from dataclasses import dataclass
from itertools import groupby
from typing import Any

from pydantic import BaseModel, validator

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

ProjectId = str


class Cost(BaseModel):
    month: datetime.datetime
    amount: float
    currency: str
    project: str

    @validator("month", pre=True)
    @classmethod
    def parse_month(cls, value: str) -> datetime.datetime:
        return datetime.datetime.strptime(value, "%Y%m")

    class Config:
        frozen = True

    def to_details(self) -> str:
        return f"{self.month.strftime('%B %Y')}: {self.amount:.2f} {self.currency}"


@dataclass(frozen=True)
class ProjectCost:
    project: str
    current_month: Cost
    previous_month: Cost | None


Section = Mapping[ProjectId, ProjectCost]


def keyfunc(x: Mapping[str, str]) -> str:
    return x["id"]


def parse(string_table: StringTable) -> Section:
    query_month = datetime.datetime.strptime(json.loads(string_table[0][0])["query_month"], "%Y%m")
    all_rows = sorted([json.loads(line[0]) for line in string_table[1:]], key=keyfunc)
    section = {}
    for project_id, rows in groupby(all_rows, key=keyfunc):
        month_costs = sorted([Cost.parse_obj(r) for r in rows], key=lambda c: c.month)
        if len(month_costs) > 1:
            cost = ProjectCost(
                current_month=month_costs[1],
                previous_month=month_costs[0],
                project=month_costs[0].project,
            )
        else:
            cost = ProjectCost(
                current_month=month_costs[0], previous_month=None, project=month_costs[0].project
            )
        if cost.current_month.month != query_month:
            continue
        section[project_id] = cost

    return section


register.agent_section(name="gcp_cost", parse_function=parse)


def discover(section: Section) -> DiscoveryResult:
    for project in section:
        yield Service(item=project)


def check(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if item not in section:
        return
    project_costs = section[item]
    current_month = project_costs.current_month
    previous_month = project_costs.previous_month
    state = State.OK
    if levels := params.get("levels"):
        if current_month.amount > levels[1]:
            state = State.CRIT
        elif current_month.amount > levels[0]:
            state = State.WARN
    prev_month_details = f", {previous_month.to_details()}" if previous_month else ""
    yield Result(
        state=state,
        summary=f"Project: {current_month.project}, Cost: {current_month.amount} {current_month.currency}",
        details=f"{current_month.to_details()}{prev_month_details}",
    )


register.check_plugin(
    name="gcp_cost",
    service_name="Costs project %s",
    discovery_function=discover,
    check_function=check,
    check_ruleset_name="gcp_cost",
    check_default_parameters={"levels": None},
)
