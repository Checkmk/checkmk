#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import collections
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    StringTable,
)
from cmk.plugins.aws.lib import parse_aws


@dataclass(frozen=True)
class CostMetric:
    amount: float
    unit: str


Section = Mapping[tuple[str, str], Mapping[str, CostMetric]]

AWSCostAndUageMetrics = [
    ("Unblended", "UnblendedCost", "unblended"),
]


def parse_aws_costs_and_usage(string_table: StringTable) -> Section:
    parsed: dict[tuple[str, str], dict[str, CostMetric]] = {}
    for row in parse_aws(string_table):
        timeperiod = row["TimePeriod"]["Start"]
        for group in row.get("Groups", []):
            service_name = " ".join(group["Keys"])
            for metric_name, metrics in group["Metrics"].items():
                try:
                    costs = float(metrics["Amount"])
                    unit = metrics["Unit"]
                except (KeyError, ValueError):
                    continue
                else:
                    parsed.setdefault((timeperiod, service_name), {}).setdefault(
                        metric_name, CostMetric(amount=costs, unit=unit)
                    )
    return parsed


#   .--summary-------------------------------------------------------------.


def discover_aws_costs_and_usage_summary(section: Section) -> DiscoveryResult:
    if section:
        yield Service(item="Summary")


def check_aws_costs_and_usage_summary(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    amounts_by_metrics: dict[tuple[str, str, str, str], float] = collections.defaultdict(float)
    for (timeperiod, _service_name), metrics in section.items():
        for title, metric_name, key in AWSCostAndUageMetrics:
            metric = metrics[metric_name]
            amounts_by_metrics[(timeperiod, title, metric.unit, key)] += metric.amount

    for (timeperiod, title, unit, key), costs in amounts_by_metrics.items():
        yield from check_levels_v1(
            costs,
            metric_name=f"aws_costs_{key}",
            levels_upper=params.get(f"levels_{key}", (None, None)),
            label=f"({timeperiod}) Total {title} {unit}",
        )


check_plugin_aws_costs_and_usage = CheckPlugin(
    name="aws_costs_and_usage",
    service_name="AWS/CE %s",
    discovery_function=discover_aws_costs_and_usage_summary,
    check_function=check_aws_costs_and_usage_summary,
    check_ruleset_name="aws_costs_and_usage",
    check_default_parameters={},
)


agent_section_aws_costs_and_usage = AgentSection(
    name="aws_costs_and_usage",
    parse_function=parse_aws_costs_and_usage,
)


#   .--per service---------------------------------------------------------.


def discover_aws_costs_and_usage_per_service(section: Section) -> DiscoveryResult:
    for _timeperiod, service_name in section:
        yield Service(item=service_name)


def check_aws_costs_and_usage_per_service(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    data = None
    timeperiod = None
    for (timeperiod, service_name), metrics in section.items():
        if item == service_name:
            data = metrics
            break
    if not data:
        return

    for title, metric_name, key in AWSCostAndUageMetrics:
        metric = data[metric_name]
        yield from check_levels_v1(
            metric.amount,
            metric_name=f"aws_costs_{key}",
            levels_upper=params.get(f"levels_{key}", (None, None)),
            label=f"({timeperiod}) {title} {metric.unit}",
        )


check_plugin_aws_costs_and_usage_per_service = CheckPlugin(
    name="aws_costs_and_usage_per_service",
    service_name="AWS/CE %s",
    sections=["aws_costs_and_usage"],
    discovery_function=discover_aws_costs_and_usage_per_service,
    check_function=check_aws_costs_and_usage_per_service,
    check_ruleset_name="aws_costs_and_usage",
    check_default_parameters={},
)
