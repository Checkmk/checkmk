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
    Service,
    StringTable,
)
from cmk.plugins.aws.lib import (
    check_aws_http_errors,
    extract_aws_metrics_by_labels,
    get_data_or_go_stale,
    parse_aws,
)

Section = Mapping[str, Mapping[str, float]]


def parse_aws_elbv2_target_groups_http(string_table: StringTable) -> Section:
    return extract_aws_metrics_by_labels(
        [
            "RequestCount",
            "HTTPCode_Target_2XX_Count",
            "HTTPCode_Target_3XX_Count",
            "HTTPCode_Target_4XX_Count",
            "HTTPCode_Target_5XX_Count",
        ],
        parse_aws(string_table),
    )


def discover_aws_application_elb_target_groups_http(section: Section) -> DiscoveryResult:
    for item, data in section.items():
        if "RequestCount" in data:
            yield Service(item=item)


def check_aws_application_elb_target_groups_http(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    data = get_data_or_go_stale(item, section)
    yield from check_aws_http_errors(
        params.get("levels_http", {}),
        data,
        ["2xx", "3xx", "4xx", "5xx"],
        "HTTPCode_Target_%s_Count",
    )


agent_section_aws_elbv2_application_target_groups_http = AgentSection(
    name="aws_elbv2_application_target_groups_http",
    parse_function=parse_aws_elbv2_target_groups_http,
)


check_plugin_aws_elbv2_application_target_groups_http = CheckPlugin(
    name="aws_elbv2_application_target_groups_http",
    service_name="AWS/ApplicationELB HTTP %s",
    discovery_function=discover_aws_application_elb_target_groups_http,
    check_function=check_aws_application_elb_target_groups_http,
    check_ruleset_name="aws_elbv2_target_errors",
    check_default_parameters={},
)
