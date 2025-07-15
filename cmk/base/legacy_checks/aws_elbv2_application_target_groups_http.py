#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.aws import check_aws_http_errors, get_data_or_go_stale
from cmk.plugins.aws.lib import extract_aws_metrics_by_labels, parse_aws

check_info = {}


def parse_aws_elbv2_target_groups_http(string_table):
    metrics = extract_aws_metrics_by_labels(
        [
            "RequestCount",
            "HTTPCode_Target_2XX_Count",
            "HTTPCode_Target_3XX_Count",
            "HTTPCode_Target_4XX_Count",
            "HTTPCode_Target_5XX_Count",
        ],
        parse_aws(string_table),
    )
    return metrics


def discover_aws_application_elb_target_groups_http(section):
    yield from ((item, {}) for item, data in section.items() if "RequestCount" in data)


def check_aws_application_elb_target_groups_http(item, params, section):
    data = get_data_or_go_stale(item, section)
    return check_aws_http_errors(
        params.get("levels_http", {}),
        data,
        ["2xx", "3xx", "4xx", "5xx"],
        "HTTPCode_Target_%s_Count",
    )


check_info["aws_elbv2_application_target_groups_http"] = LegacyCheckDefinition(
    name="aws_elbv2_application_target_groups_http",
    parse_function=parse_aws_elbv2_target_groups_http,
    service_name="AWS/ApplicationELB HTTP %s",
    discovery_function=discover_aws_application_elb_target_groups_http,
    check_function=check_aws_application_elb_target_groups_http,
    check_ruleset_name="aws_elbv2_target_errors",
)
