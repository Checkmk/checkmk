#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.aws import (
    aws_get_parsed_item_data,
    check_aws_error_rate,
    check_aws_request_rate,
)
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import IgnoreResultsError
from cmk.base.plugins.agent_based.utils.aws import extract_aws_metrics_by_labels, parse_aws


def parse_aws_elbv2_target_groups_lambda(info):
    metrics = extract_aws_metrics_by_labels(["RequestCount", "LambdaUserError"], parse_aws(info))
    return metrics


def discover_aws_elbv2_target_groups_lambda(section):
    yield from ((item, {}) for item, data in section.items() if "RequestCount" in data)


@aws_get_parsed_item_data
def check_aws_application_elb_target_groups_lambda(item, params, data):
    request_rate = data.get("RequestCount")
    if request_rate is None:
        raise IgnoreResultsError("Currently no data from AWS")

    yield check_aws_request_rate(request_rate)

    lambda_error_rate = data.get("LambdaUserError")
    if lambda_error_rate is None:
        lambda_error_rate = 0  # CloudWatch only reports LambdaUserError if the value is nonzero

    for result in check_aws_error_rate(
        lambda_error_rate,
        request_rate,
        "aws_lambda_users_errors_rate",
        "aws_lambda_users_errors_perc",
        params.get("levels_lambda", {}),
        "Lambda user errors",
    ):
        yield result


check_info["aws_elbv2_application_target_groups_lambda"] = LegacyCheckDefinition(
    parse_function=parse_aws_elbv2_target_groups_lambda,
    discovery_function=discover_aws_elbv2_target_groups_lambda,
    check_function=check_aws_application_elb_target_groups_lambda,
    service_name="AWS/ApplicationELB Lambda %s",
    check_ruleset_name="aws_elbv2_target_errors",
)
