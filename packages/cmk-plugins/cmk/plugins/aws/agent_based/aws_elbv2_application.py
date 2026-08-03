#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    StringTable,
)
from cmk.plugins.aws.lib import (
    aws_get_bytes_rate_human_readable,
    aws_get_counts_rate_human_readable,
    aws_get_float_human_readable,
    AWSMetric,
    check_aws_http_errors,
    check_aws_metrics,
    discover_aws_generic_single,
    extract_aws_metrics_by_labels,
    parse_aws,
)

Section = Mapping[str, float]


def parse_aws_elbv2_application(string_table: StringTable) -> Section:
    metrics = extract_aws_metrics_by_labels(
        [
            "ConsumedLCUs",
            "ActiveConnectionCount",
            "NewConnectionCount",
            "RejectedConnectionCount",
            "ClientTLSNegotiationErrorCount",
            "RequestCount",
            "HTTPCode_ELB_3XX_Count",
            "HTTPCode_ELB_4XX_Count",
            "HTTPCode_ELB_5XX_Count",
            "HTTPCode_ELB_500_Count",
            "HTTPCode_ELB_502_Count",
            "HTTPCode_ELB_503_Count",
            "HTTPCode_ELB_504_Count",
            "HTTP_Fixed_Response_Count",
            "HTTP_Redirect_Count",
            "HTTP_Redirect_Url_Limit_Exceeded_Count",
            "ProcessedBytes",
            "RuleEvaluations",
            "IPv6ProcessedBytes",
            "IPv6RequestCount",
        ],
        parse_aws(string_table),
    )
    # We get exactly one entry: {INST-ID: METRICS}
    # INST-ID is the piggyback host name
    try:
        return list(metrics.values())[-1]
    except IndexError:
        return {}


#   .--LCU-----------------------------------------------------------------.


def check_aws_elbv2_application_lcu(params: Mapping[str, Any], section: Section) -> CheckResult:
    lcus = section.get("ConsumedLCUs")
    if lcus is None:
        raise IgnoreResultsError("Currently no data from AWS")
    yield from check_levels_v1(
        lcus,
        metric_name="aws_consumed_lcus",
        levels_upper=params.get("levels"),
        render_func=aws_get_float_human_readable,
        label="Consumption",
    )


def discover_aws_elbv2_application(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(section, ["ConsumedLCUs"])


agent_section_aws_elbv2_application = AgentSection(
    name="aws_elbv2_application",
    parse_function=parse_aws_elbv2_application,
)


check_plugin_aws_elbv2_application = CheckPlugin(
    name="aws_elbv2_application",
    service_name="AWS/ApplicationELB LCUs",
    discovery_function=discover_aws_elbv2_application,
    check_function=check_aws_elbv2_application_lcu,
    check_ruleset_name="aws_elbv2_lcu",
    check_default_parameters={},
)


#   .--connections---------------------------------------------------------.

_aws_elbv2_application_connection_types = [
    "ActiveConnectionCount",
    "NewConnectionCount",
    "RejectedConnectionCount",
    "ClientTLSNegotiationErrorCount",
]


def check_aws_elbv2_application_connections(section: Section) -> CheckResult:
    yield from check_aws_metrics(
        [
            AWSMetric(
                value=value,
                name="aws_client_tls_errors" if key == "tls_errors" else f"aws_{key}_connections",
                label=info_name,
                render_func=aws_get_counts_rate_human_readable,
            )
            for cw_metric_name, (info_name, key) in zip(
                _aws_elbv2_application_connection_types,
                [
                    ("Active", "active"),
                    ("New", "new"),
                    ("Rejected", "rejected"),
                    ("TLS errors", "tls_errors"),
                ],
            )
            if (value := section.get(cw_metric_name)) is not None
        ]
    )


def discover_aws_elbv2_application_connections(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(
        section, _aws_elbv2_application_connection_types, requirement=any
    )


check_plugin_aws_elbv2_application_connections = CheckPlugin(
    name="aws_elbv2_application_connections",
    service_name="AWS/ApplicationELB Connections",
    sections=["aws_elbv2_application"],
    discovery_function=discover_aws_elbv2_application_connections,
    check_function=check_aws_elbv2_application_connections,
)


#   .--HTTP ELB------------------------------------------------------------.


def check_aws_elbv2_application_http_elb(
    params: Mapping[str, Any], section: Section
) -> CheckResult:
    yield from check_aws_http_errors(
        params.get("levels_load_balancers", params),
        section,
        ["3xx", "4xx", "5xx", "500", "502", "503", "504"],
        "HTTPCode_ELB_%s_Count",
    )


def discover_aws_elbv2_application_http_elb(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(section, ["RequestCount"])


check_plugin_aws_elbv2_application_http_elb = CheckPlugin(
    name="aws_elbv2_application_http_elb",
    service_name="AWS/ApplicationELB HTTP ELB",
    sections=["aws_elbv2_application"],
    discovery_function=discover_aws_elbv2_application_http_elb,
    check_function=check_aws_elbv2_application_http_elb,
    check_ruleset_name="aws_elb_http",
    check_default_parameters={},
)


#   .--HTTP redirects------------------------------------------------------.

_aws_elbv2_application_http_redirects_metrics = [
    "HTTP_Redirect_Count",
    "HTTP_Redirect_Url_Limit_Exceeded_Count",
    "HTTP_Fixed_Response_Count",
]


def check_aws_elbv2_application_http_redirects(section: Section) -> CheckResult:
    yield from check_aws_metrics(
        [
            AWSMetric(
                value=value,
                name=f"aws_{key}",
                label=info_name,
                render_func=aws_get_counts_rate_human_readable,
            )
            for cw_metric_name, (info_name, key) in zip(
                _aws_elbv2_application_http_redirects_metrics,
                [
                    ("Successful", "http_redirects"),
                    ("Not completed", "http_redirect_url_limit"),
                    ("Successful fixed responses", "http_fixed_response"),
                ],
            )
            if (value := section.get(cw_metric_name)) is not None
        ]
    )


def discover_aws_elbv2_application_http_redirects(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(
        section, _aws_elbv2_application_http_redirects_metrics, requirement=any
    )


check_plugin_aws_elbv2_application_http_redirects = CheckPlugin(
    name="aws_elbv2_application_http_redirects",
    service_name="AWS/ApplicationELB HTTP Redirects",
    sections=["aws_elbv2_application"],
    discovery_function=discover_aws_elbv2_application_http_redirects,
    check_function=check_aws_elbv2_application_http_redirects,
)


#   .--statistics----------------------------------------------------------.

_aws_elbv2_application_statistics_metrics = [
    "ProcessedBytes",
    "IPv6ProcessedBytes",
    "IPv6RequestCount",
    "RuleEvaluations",
]


def check_aws_elbv2_application_statistics(section: Section) -> CheckResult:
    yield from check_aws_metrics(
        [
            AWSMetric(
                value=value,
                name=metric_name,
                label=info_name,
                render_func=(
                    aws_get_bytes_rate_human_readable
                    if "bytes" in metric_name
                    else aws_get_counts_rate_human_readable
                ),
            )
            for cw_metric_name, (info_name, metric_name) in zip(
                _aws_elbv2_application_statistics_metrics,
                [
                    ("Processed bytes", "aws_proc_bytes"),
                    ("IPv6 Processed bytes", "aws_ipv6_proc_bytes"),
                    ("IPv6RequestCount", "aws_ipv6_requests"),
                    ("Rule evaluations", "aws_rule_evaluations"),
                ],
            )
            if (value := section.get(cw_metric_name)) is not None
        ]
    )


def discover_aws_elbv2_application_statistics(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(
        section, _aws_elbv2_application_statistics_metrics, requirement=any
    )


check_plugin_aws_elbv2_application_statistics = CheckPlugin(
    name="aws_elbv2_application_statistics",
    service_name="AWS/ApplicationELB Statistics",
    sections=["aws_elbv2_application"],
    discovery_function=discover_aws_elbv2_application_statistics,
    check_function=check_aws_elbv2_application_statistics,
)
