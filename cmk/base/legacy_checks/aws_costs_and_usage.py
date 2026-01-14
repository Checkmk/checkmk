#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


# mypy: disable-error-code="var-annotated"

import collections

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.base.check_legacy_includes.aws import parse_aws

check_info = {}

AWSCostAndUageMetrics = [
    ("Unblended", "UnblendedCost", "unblended"),
]


def parse_aws_costs_and_usage(string_table):
    parsed = {}
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
                        metric_name, (costs, unit)
                    )
    return parsed


#   .--summary-------------------------------------------------------------.
#   |                                                                      |
#   |           ___ _   _ _ __ ___  _ __ ___   __ _ _ __ _   _             |
#   |          / __| | | | '_ ` _ \| '_ ` _ \ / _` | '__| | | |            |
#   |          \__ \ |_| | | | | | | | | | | | (_| | |  | |_| |            |
#   |          |___/\__,_|_| |_| |_|_| |_| |_|\__,_|_|   \__, |            |
#   |                                                    |___/             |
#   '----------------------------------------------------------------------'


def discover_aws_costs_and_usage_summary(parsed):
    if parsed:
        return [("Summary", {})]
    return []


def check_aws_costs_and_usage_summary(item, params, parsed):
    amounts_by_metrics = collections.defaultdict(float)
    for (timeperiod, _service_name), metrics in parsed.items():
        for (
            title,
            metric_name,
            key,
        ) in AWSCostAndUageMetrics:
            costs, unit = metrics[metric_name]
            amounts_by_metrics[(timeperiod, title, unit, key)] += costs

    for (timeperiod, title, unit, key), costs in amounts_by_metrics.items():
        yield check_levels(
            costs,
            "aws_costs_%s" % key,
            params.get("levels_%s" % key, (None, None)),
            infoname=f"({timeperiod}) Total {title} {unit}",
        )


check_info["aws_costs_and_usage"] = LegacyCheckDefinition(
    name="aws_costs_and_usage",
    parse_function=parse_aws_costs_and_usage,
    service_name="AWS/CE %s",
    discovery_function=discover_aws_costs_and_usage_summary,
    check_function=check_aws_costs_and_usage_summary,
    check_ruleset_name="aws_costs_and_usage",
)

# .
#   .--per service---------------------------------------------------------.
#   |                                                _                     |
#   |          _ __   ___ _ __   ___  ___ _ ____   _(_) ___ ___            |
#   |         | '_ \ / _ \ '__| / __|/ _ \ '__\ \ / / |/ __/ _ \           |
#   |         | |_) |  __/ |    \__ \  __/ |   \ V /| | (_|  __/           |
#   |         | .__/ \___|_|    |___/\___|_|    \_/ |_|\___\___|           |
#   |         |_|                                                          |
#   '----------------------------------------------------------------------'


def discover_aws_costs_and_usage_per_service(parsed):
    for _timeperiod, service_name in parsed:
        yield service_name, {}


def check_aws_costs_and_usage_per_service(item, params, parsed):
    data = None
    timeperiod = None
    for (timeperiod, service_name), metrics in parsed.items():
        if item == service_name:
            data = metrics
            break
    if not data:
        return

    for title, metric_name, key in AWSCostAndUageMetrics:
        costs, unit = data[metric_name]
        yield check_levels(
            costs,
            "aws_costs_%s" % key,
            params.get("levels_%s" % key, (None, None)),
            infoname=f"({timeperiod}) {title} {unit}",
        )


check_info["aws_costs_and_usage.per_service"] = LegacyCheckDefinition(
    name="aws_costs_and_usage_per_service",
    service_name="AWS/CE %s",
    sections=["aws_costs_and_usage"],
    discovery_function=discover_aws_costs_and_usage_per_service,
    check_function=check_aws_costs_and_usage_per_service,
    check_ruleset_name="aws_costs_and_usage",
)
