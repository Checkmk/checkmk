#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Service,
    StringTable,
)
from cmk.plugins.aws.lib import (
    check_aws_error_rate,
    check_aws_request_rate,
    extract_aws_metrics_by_labels,
    get_data_or_go_stale,
    parse_aws,
)

Section = Mapping[str, Mapping[str, float]]


def parse_aws_elbv2_target_groups_lambda(string_table: StringTable) -> Section:
    return extract_aws_metrics_by_labels(
        ["RequestCount", "LambdaUserError"], parse_aws(string_table)
    )


def discover_aws_elbv2_target_groups_lambda(section: Section) -> DiscoveryResult:
    for item, data in section.items():
        if "RequestCount" in data:
            yield Service(item=item)


def check_aws_application_elb_target_groups_lambda(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    data = get_data_or_go_stale(item, section)
    request_rate = data.get("RequestCount")
    if request_rate is None:
        raise IgnoreResultsError("Currently no data from AWS")

    yield from check_aws_request_rate(request_rate)

    lambda_error_rate = data.get("LambdaUserError")
    if lambda_error_rate is None:
        lambda_error_rate = 0  # CloudWatch only reports LambdaUserError if the value is nonzero

    yield from check_aws_error_rate(
        lambda_error_rate,
        request_rate,
        "aws_lambda_users_errors_rate",
        "aws_lambda_users_errors_perc",
        params.get("levels_lambda"),
        "Lambda user errors",
    )


agent_section_aws_elbv2_application_target_groups_lambda = AgentSection(
    name="aws_elbv2_application_target_groups_lambda",
    parse_function=parse_aws_elbv2_target_groups_lambda,
)


check_plugin_aws_elbv2_application_target_groups_lambda = CheckPlugin(
    name="aws_elbv2_application_target_groups_lambda",
    service_name="AWS/ApplicationELB Lambda %s",
    discovery_function=discover_aws_elbv2_target_groups_lambda,
    check_function=check_aws_application_elb_target_groups_lambda,
    check_ruleset_name="aws_elbv2_target_errors",
    check_default_parameters={},
)
