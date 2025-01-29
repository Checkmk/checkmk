#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from datetime import date
from typing import TypedDict

from pydantic import BaseModel

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v1 import Result, Service, State
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    render,
    StringTable,
)
from cmk.plugins.aws.lib import parse_aws


def _rm_trailing_zeros(s: float) -> str:
    return f"{s:.2f}".rstrip("0").rstrip(".")


class ReservationUtilization(BaseModel):
    UtilizationPercentage: float
    PurchasedHours: float
    TotalActualHours: float


Section = dict[str, ReservationUtilization]


class UtilizationParams(TypedDict):
    levels_utilization_percent: tuple[float, float] | None


def parse_aws_reservation_utilization(string_table: StringTable) -> Section:
    parsed: Section = {}
    for row in parse_aws(string_table):
        timeperiod = row["TimePeriod"]["Start"]
        data = ReservationUtilization.model_validate(row["Total"], strict=False)
        parsed[timeperiod] = data
    return parsed


agent_section_aws_reservation_utilization = AgentSection(
    name="aws_reservation_utilization",
    parse_function=parse_aws_reservation_utilization,
)


def discover_aws_reservation_utilization(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_aws_reservation_utilization(params: UtilizationParams, section: Section) -> CheckResult:
    if not section:
        raise IgnoreResultsError("Currently no data from AWS")

    latest_date = max(date.fromisoformat(d) for d in section.keys()).strftime("%Y-%m-%d")
    data = section[latest_date]

    yield from check_levels_v1(
        value=data.UtilizationPercentage,
        metric_name="aws_total_reservation_utilization",
        levels_lower=params.get("levels_utilization_percent"),
        label=f"({latest_date}) Total Reservation Utilization",
        render_func=render.percent,
    )
    yield Result(
        state=State.OK,
        summary=f"Reserved Hours: {_rm_trailing_zeros(data.PurchasedHours)}",
    )
    yield Result(
        state=State.OK,
        summary=f"Actual Hours: {_rm_trailing_zeros(data.TotalActualHours)}",
    )


check_plugin_aws_reservation_utilization = CheckPlugin(
    name="aws_reservation_utilization",
    service_name="AWS/CE Total Reservation Utilization",
    discovery_function=discover_aws_reservation_utilization,
    check_function=check_aws_reservation_utilization,
    check_default_parameters={},
    check_ruleset_name="aws_reservation_utilization",
)
