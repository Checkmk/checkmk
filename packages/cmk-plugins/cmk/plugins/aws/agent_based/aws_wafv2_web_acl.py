#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    render,
    Service,
)
from cmk.plugins.aws.lib import (
    aws_get_counts_rate_human_readable,
    extract_aws_metrics_by_labels,
    parse_aws,
)


def parse_aws_wafv2_web_acl(string_table: list[list[str]]) -> Mapping[str, float]:
    metrics = extract_aws_metrics_by_labels(
        ["AllowedRequests", "BlockedRequests"], parse_aws(string_table)
    )
    try:
        return list(metrics.values())[-1]
    except IndexError:
        return {}


def discover_aws_wafv2_web_acl(section: Mapping[str, float]) -> DiscoveryResult:
    if any(metric in section for metric in ("AllowedRequests", "BlockedRequests")):
        yield Service()


def check_aws_wafv2_web_acl(params: Mapping[str, Any], section: Mapping[str, float]) -> CheckResult:
    if len(section) == 0:
        raise IgnoreResultsError("Currently no data from AWS")

    metric_ids = ["AllowedRequests", "BlockedRequests"]
    # the metrics used here are only reported if they are not zero
    metric_vals = [section.get(metric_id, 0) for metric_id in metric_ids]
    requests_total = sum(metric_vals)

    yield from check_levels(
        requests_total,
        metric_name="aws_wafv2_requests_rate",
        render_func=aws_get_counts_rate_human_readable,
        label="Total requests",
    )

    for metric_id, metric_val in zip(metric_ids, metric_vals):
        # split at uppercase letters
        metric_id_split = [s.lower() for s in re.split("([A-Z][^A-Z]*)", metric_id) if s]
        metric_id_joined = "_".join(metric_id_split)
        metric_id_readable = " ".join(metric_id_split)

        yield from check_levels(
            metric_val,
            metric_name=f"aws_wafv2_{metric_id_joined}_rate",
            render_func=aws_get_counts_rate_human_readable,
            label=metric_id_readable.capitalize(),
        )

        try:
            perc = 100 * metric_val / requests_total
        except ZeroDivisionError:
            perc = 0

        yield from check_levels(
            perc,
            levels_upper=params.get(f"{metric_id_joined}_perc"),
            metric_name=f"aws_wafv2_{metric_id_joined}_perc",
            render_func=render.percent,
            label=f"Percentage {metric_id_readable}",
        )


agent_section_aws_wafv2_web_acl = AgentSection(
    name="aws_wafv2_web_acl",
    parse_function=parse_aws_wafv2_web_acl,
)


check_plugin_aws_wafv2_web_acl = CheckPlugin(
    name="aws_wafv2_web_acl",
    service_name="AWS/WAFV2 Web ACL Requests",
    discovery_function=discover_aws_wafv2_web_acl,
    check_function=check_aws_wafv2_web_acl,
    check_ruleset_name="aws_wafv2_web_acl",
    check_default_parameters={},
)
