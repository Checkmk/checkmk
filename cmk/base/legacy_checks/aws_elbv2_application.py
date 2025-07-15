#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import IgnoreResultsError
from cmk.base.check_legacy_includes.aws import (
    aws_get_bytes_rate_human_readable,
    aws_get_counts_rate_human_readable,
    aws_get_float_human_readable,
    check_aws_http_errors,
    check_aws_metrics,
    inventory_aws_generic_single,
    MetricInfo,
)
from cmk.plugins.aws.lib import extract_aws_metrics_by_labels, parse_aws

check_info = {}


def parse_aws_elbv2_application(string_table):
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
#   |                          _     ____ _   _                            |
#   |                         | |   / ___| | | |                           |
#   |                         | |  | |   | | | |                           |
#   |                         | |__| |___| |_| |                           |
#   |                         |_____\____|\___/                            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_aws_elbv2_application_lcu(item, params, parsed):
    lcus = parsed.get("ConsumedLCUs")
    if lcus is None:
        raise IgnoreResultsError("Currently no data from AWS")
    yield check_levels(
        lcus,
        "aws_consumed_lcus",
        params.get("levels"),
        human_readable_func=aws_get_float_human_readable,
        infoname="Consumption",
    )


def discover_aws_elbv2_application(p):
    return inventory_aws_generic_single(p, ["ConsumedLCUs"])


check_info["aws_elbv2_application"] = LegacyCheckDefinition(
    name="aws_elbv2_application",
    parse_function=parse_aws_elbv2_application,
    service_name="AWS/ApplicationELB LCUs",
    discovery_function=discover_aws_elbv2_application,
    check_function=check_aws_elbv2_application_lcu,
    check_ruleset_name="aws_elbv2_lcu",
)

# .
#   .--connections---------------------------------------------------------.
#   |                                        _   _                         |
#   |         ___ ___  _ __  _ __   ___  ___| |_(_) ___  _ __  ___         |
#   |        / __/ _ \| '_ \| '_ \ / _ \/ __| __| |/ _ \| '_ \/ __|        |
#   |       | (_| (_) | | | | | | |  __/ (__| |_| | (_) | | | \__ \        |
#   |        \___\___/|_| |_|_| |_|\___|\___|\__|_|\___/|_| |_|___/        |
#   |                                                                      |
#   '----------------------------------------------------------------------'

_aws_elbv2_application_connection_types = [
    "ActiveConnectionCount",
    "NewConnectionCount",
    "RejectedConnectionCount",
    "ClientTLSNegotiationErrorCount",
]


def check_aws_elbv2_application_connections(item, params, parsed):
    return check_aws_metrics(
        [
            MetricInfo(
                metric_val=parsed.get(cw_metric_name),
                metric_name="aws_client_tls_errors"
                if key == "tls_errors"
                else f"aws_{key}_connections",
                info_name=info_name,
                human_readable_func=aws_get_counts_rate_human_readable,
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
        ]
    )


def discover_aws_elbv2_application_connections(p):
    return inventory_aws_generic_single(p, _aws_elbv2_application_connection_types, requirement=any)


check_info["aws_elbv2_application.connections"] = LegacyCheckDefinition(
    name="aws_elbv2_application_connections",
    service_name="AWS/ApplicationELB Connections",
    sections=["aws_elbv2_application"],
    discovery_function=discover_aws_elbv2_application_connections,
    check_function=check_aws_elbv2_application_connections,
)

# .
#   .--HTTP ELB------------------------------------------------------------.
#   |             _   _ _____ _____ ____    _____ _     ____               |
#   |            | | | |_   _|_   _|  _ \  | ____| |   | __ )              |
#   |            | |_| | | |   | | | |_) | |  _| | |   |  _ \              |
#   |            |  _  | | |   | | |  __/  | |___| |___| |_) |             |
#   |            |_| |_| |_|   |_| |_|     |_____|_____|____/              |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_aws_elbv2_application_http_elb(item, params, parsed):
    return check_aws_http_errors(
        params.get("levels_load_balancers", params),
        parsed,
        ["3xx", "4xx", "5xx", "500", "502", "503", "504"],
        "HTTPCode_ELB_%s_Count",
    )


def discover_aws_elbv2_application_http_elb(p):
    return inventory_aws_generic_single(p, ["RequestCount"])


check_info["aws_elbv2_application.http_elb"] = LegacyCheckDefinition(
    name="aws_elbv2_application_http_elb",
    service_name="AWS/ApplicationELB HTTP ELB",
    sections=["aws_elbv2_application"],
    discovery_function=discover_aws_elbv2_application_http_elb,
    check_function=check_aws_elbv2_application_http_elb,
    check_ruleset_name="aws_elb_http",
)

# .
#   .--HTTP redirects------------------------------------------------------.
#   |  _   _ _____ _____ ____                 _ _               _          |
#   | | | | |_   _|_   _|  _ \   _ __ ___  __| (_)_ __ ___  ___| |_ ___    |
#   | | |_| | | |   | | | |_) | | '__/ _ \/ _` | | '__/ _ \/ __| __/ __|   |
#   | |  _  | | |   | | |  __/  | | |  __/ (_| | | | |  __/ (__| |_\__ \   |
#   | |_| |_| |_|   |_| |_|     |_|  \___|\__,_|_|_|  \___|\___|\__|___/   |
#   |                                                                      |
#   '----------------------------------------------------------------------'

_aws_elbv2_application_http_redirects_metrics = [
    "HTTP_Redirect_Count",
    "HTTP_Redirect_Url_Limit_Exceeded_Count",
    "HTTP_Fixed_Response_Count",
]


def check_aws_elbv2_application_http_redirects(item, params, parsed):
    return check_aws_metrics(
        [
            {
                "metric_val": parsed.get(cw_metric_name),
                "metric_name": "aws_%s" % key,
                "info_name": info_name,
                "human_readable_func": aws_get_counts_rate_human_readable,
            }
            for cw_metric_name, (info_name, key) in zip(
                _aws_elbv2_application_http_redirects_metrics,
                [
                    ("Successful", "http_redirects"),
                    ("Not completed", "http_redirect_url_limit"),
                    ("Successful fixed responses", "http_fixed_response"),
                ],
            )
        ]
    )


def discover_aws_elbv2_application_http_redirects(p):
    return inventory_aws_generic_single(
        p, _aws_elbv2_application_http_redirects_metrics, requirement=any
    )


check_info["aws_elbv2_application.http_redirects"] = LegacyCheckDefinition(
    name="aws_elbv2_application_http_redirects",
    service_name="AWS/ApplicationELB HTTP Redirects",
    sections=["aws_elbv2_application"],
    discovery_function=discover_aws_elbv2_application_http_redirects,
    check_function=check_aws_elbv2_application_http_redirects,
)

# .
#   .--statistics----------------------------------------------------------.
#   |                    _        _   _     _   _                          |
#   |                ___| |_ __ _| |_(_)___| |_(_) ___ ___                 |
#   |               / __| __/ _` | __| / __| __| |/ __/ __|                |
#   |               \__ \ || (_| | |_| \__ \ |_| | (__\__ \                |
#   |               |___/\__\__,_|\__|_|___/\__|_|\___|___/                |
#   |                                                                      |
#   '----------------------------------------------------------------------'

_aws_elbv2_application_statistics_metrics = [
    "ProcessedBytes",
    "IPv6ProcessedBytes",
    "IPv6RequestCount",
    "RuleEvaluations",
]


def check_aws_elbv2_application_statistics(item, params, parsed):
    metric_infos = []

    for cw_metric_name, (info_name, metric_name) in zip(
        _aws_elbv2_application_statistics_metrics,
        [
            ("Processed bytes", "aws_proc_bytes"),
            ("IPv6 Processed bytes", "aws_ipv6_proc_bytes"),
            ("IPv6RequestCount", "aws_ipv6_requests"),
            ("Rule evaluations", "aws_rule_evaluations"),
        ],
    ):
        if "bytes" in metric_name:
            human_readable_func = aws_get_bytes_rate_human_readable
        else:
            human_readable_func = aws_get_counts_rate_human_readable

        metric_infos.append(
            MetricInfo(
                metric_val=parsed.get(cw_metric_name),
                metric_name=metric_name,
                info_name=info_name,
                human_readable_func=human_readable_func,
            )
        )

    return check_aws_metrics(metric_infos)


def discover_aws_elbv2_application_statistics(p):
    return inventory_aws_generic_single(
        p, _aws_elbv2_application_statistics_metrics, requirement=any
    )


check_info["aws_elbv2_application.statistics"] = LegacyCheckDefinition(
    name="aws_elbv2_application_statistics",
    service_name="AWS/ApplicationELB Statistics",
    sections=["aws_elbv2_application"],
    discovery_function=discover_aws_elbv2_application_statistics,
    check_function=check_aws_elbv2_application_statistics,
)
