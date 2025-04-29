#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    LevelsT,
    render,
)
from cmk.plugins.aws.lib import discover_aws_generic_single


def inventory_aws_dynamodb_latency(section: Mapping[str, float]) -> DiscoveryResult:
    yield from discover_aws_generic_single(
        section,
        [
            "Query_Average_SuccessfulRequestLatency",
            "GetItem_Average_SuccessfulRequestLatency",
            "PutItem_Average_SuccessfulRequestLatency",
        ],
        requirement=any,
    )


def check_aws_dynamodb_latency(
    params: Mapping[str, None | tuple[float, float]], section: Mapping[str, float]
) -> CheckResult:
    go_stale = True

    for operation in ["Query", "GetItem", "PutItem"]:
        for statistic in ["Average", "Maximum"]:
            metric_name = f"aws_dynamodb_{operation.lower()}_{statistic.lower()}_latency"
            metric_id = f"{operation}_{statistic}_SuccessfulRequestLatency"
            metric_value = section.get(metric_id)

            if metric_value is not None:
                go_stale = False

                # SuccessfulRequestLatency and levels come in ms
                metric_value *= 1e-3
                levels: tuple[float, float] | None = None
                levels = params.get(f"levels_seconds_{operation.lower()}_{statistic.lower()}")
                levels_upper: LevelsT = ("no_levels", None)
                if levels is not None and len(levels) == 2:
                    levels_upper = ("fixed", (levels[0] * 1e-3, levels[1] * 1e-3))

                yield from check_levels(
                    value=metric_value,
                    metric_name=metric_name,
                    levels_upper=levels_upper,
                    label=f"{statistic} latency {operation}",
                    render_func=render.timespan,
                )

    if go_stale:
        raise IgnoreResultsError("Currently no data from AWS")


check_plugin_aws_dynamodb_table_latency = CheckPlugin(
    name="aws_dynamodb_table_latency",
    service_name="AWS/DynamoDB Latency",
    sections=["aws_dynamodb_table"],
    discovery_function=inventory_aws_dynamodb_latency,
    check_function=check_aws_dynamodb_latency,
    check_ruleset_name="aws_dynamodb_latency",
    check_default_parameters={},
)
