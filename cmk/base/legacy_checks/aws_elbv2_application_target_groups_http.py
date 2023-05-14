#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import discover, LegacyCheckDefinition
from cmk.base.check_legacy_includes.aws import aws_get_parsed_item_data, check_aws_http_errors
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.utils.aws import extract_aws_metrics_by_labels, parse_aws


def parse_aws_elbv2_target_groups_http(info):
    metrics = extract_aws_metrics_by_labels(
        [
            "RequestCount",
            "HTTPCode_Target_2XX_Count",
            "HTTPCode_Target_3XX_Count",
            "HTTPCode_Target_4XX_Count",
            "HTTPCode_Target_5XX_Count",
        ],
        parse_aws(info),
    )
    return metrics


@aws_get_parsed_item_data
def check_aws_application_elb_target_groups_http(item, params, data):
    return check_aws_http_errors(
        params.get("levels_http", {}),
        data,
        ["2xx", "3xx", "4xx", "5xx"],
        "HTTPCode_Target_%s_Count",
    )


check_info["aws_elbv2_application_target_groups_http"] = LegacyCheckDefinition(
    parse_function=parse_aws_elbv2_target_groups_http,
    discovery_function=discover(lambda k, v: "RequestCount" in v),
    check_function=check_aws_application_elb_target_groups_http,
    service_name="AWS/ApplicationELB HTTP %s",
    check_ruleset_name="aws_elbv2_target_errors",
)
