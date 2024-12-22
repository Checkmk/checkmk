#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.aws import (
    aws_get_bytes_rate_human_readable,
    aws_get_counts_rate_human_readable,
    aws_get_float_human_readable,
    check_aws_metrics,
    inventory_aws_generic_single,
    MetricInfo,
)

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import IgnoreResultsError
from cmk.plugins.aws.lib import extract_aws_metrics_by_labels, parse_aws

check_info = {}


def parse_aws_elbv2_network(string_table):
    metrics = extract_aws_metrics_by_labels(
        [
            "ConsumedLCUs",
            "ActiveFlowCount",
            "ActiveFlowCount_TLS",
            "NewFlowCount",
            "NewFlowCount_TLS",
            "HealthyHostCount",
            "UnHealthyHostCount",
            "ProcessedBytes",
            "ProcessedBytes_TLS",
            "ClientTLSNegotiationErrorCount",
            "TargetTLSNegotiationErrorCount",
            "TCP_Client_Reset_Count",
            "TCP_ELB_Reset_Count",
            "TCP_Target_Reset_Count",
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


def check_aws_elbv2_network_lcu(item, params, parsed):
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


def discover_aws_elbv2_network(p):
    return inventory_aws_generic_single(p, ["ConsumedLCUs"])


check_info["aws_elbv2_network"] = LegacyCheckDefinition(
    name="aws_elbv2_network",
    parse_function=parse_aws_elbv2_network,
    service_name="AWS/NetworkELB LCUs",
    discovery_function=discover_aws_elbv2_network,
    check_function=check_aws_elbv2_network_lcu,
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

_aws_elbv2_network_connection_types = [
    "ActiveFlowCount",
    "ActiveFlowCount_TLS",
    "NewFlowCount",
    "NewFlowCount_TLS",
]


def check_aws_elbv2_network_connections(item, params, parsed):
    return check_aws_metrics(
        [
            MetricInfo(
                metric_val=parsed.get(cw_metric_name),
                metric_name="aws_%s_connections" % key,
                info_name=info_name,
                human_readable_func=aws_get_counts_rate_human_readable,
            )
            for cw_metric_name, (info_name, key) in zip(
                _aws_elbv2_network_connection_types,
                [
                    ("Active", "active"),
                    ("Active TLS", "active_tls"),
                    ("New", "new"),
                    ("New TLS", "new_tls"),
                ],
            )
        ]
    )


def discover_aws_elbv2_network_connections(p):
    return inventory_aws_generic_single(p, _aws_elbv2_network_connection_types, requirement=any)


check_info["aws_elbv2_network.connections"] = LegacyCheckDefinition(
    name="aws_elbv2_network_connections",
    service_name="AWS/NetworkELB Connections",
    sections=["aws_elbv2_network"],
    discovery_function=discover_aws_elbv2_network_connections,
    check_function=check_aws_elbv2_network_connections,
)

# .
#   .--Healthy hosts-------------------------------------------------------.
#   |    _   _            _ _   _             _               _            |
#   |   | | | | ___  __ _| | |_| |__  _   _  | |__   ___  ___| |_ ___      |
#   |   | |_| |/ _ \/ _` | | __| '_ \| | | | | '_ \ / _ \/ __| __/ __|     |
#   |   |  _  |  __/ (_| | | |_| | | | |_| | | | | | (_) \__ \ |_\__ \     |
#   |   |_| |_|\___|\__,_|_|\__|_| |_|\__, | |_| |_|\___/|___/\__|___/     |
#   |                                 |___/                                |
#   '----------------------------------------------------------------------'

# This service is currently never discovered, because the AWS special agent does not deliver the
# corresponding data. After fixing this issue in the special agent, probably the best solution is to
# discover one service per target group.

# def check_aws_elbv2_network_healthy_hosts(item, params, parsed):
#     try:
#         healthy_hosts = int(parsed["HealthyHostCount"])
#     except (KeyError, ValueError):
#         healthy_hosts = None
#
#     try:
#         unhealthy_hosts = int(parsed["UnHealthyHostCount"])
#     except (KeyError, ValueError):
#         unhealthy_hosts = None
#
#     if healthy_hosts is not None:
#         yield 0, 'Healthy hosts: %s' % healthy_hosts
#
#     if unhealthy_hosts is not None:
#         yield 0, 'Unhealthy hosts: %s' % unhealthy_hosts
#
#     if healthy_hosts is not None and unhealthy_hosts is not None:
#         total_hosts = unhealthy_hosts + healthy_hosts
#         yield 0, 'Total: %s' % total_hosts
#
#         try:
#             perc = 100.0 * healthy_hosts / total_hosts
#         except ZeroDivisionError:
#             perc = None
#
#         if perc is not None:
#             yield check_levels(perc,
#                                'aws_overall_hosts_health_perc',
#                                params.get('levels_overall_hosts_health_perc'),
#                                human_readable_func=render.percent,
#                                infoname="Proportion of healthy hosts")
#
#
# check_info['aws_elbv2_network.healthy_hosts'] = {
#     'inventory_function': lambda p: inventory_aws_generic_single(
#         p, ['HealthyHostCount', 'UnHealthyHostCount']),
#     'check_function': check_aws_elbv2_network_healthy_hosts,
#     'service_description': 'AWS/NetworkELB Healthy Hosts',
#     'group': 'aws_elb_healthy_hosts',
# }

# .
#   .--TLS handshakes------------------------------------------------------.
#   |                          _____ _     ____                            |
#   |                         |_   _| |   / ___|                           |
#   |                           | | | |   \___ \                           |
#   |                           | | | |___ ___) |                          |
#   |                           |_| |_____|____/                           |
#   |                                                                      |
#   |        _                     _     _           _                     |
#   |       | |__   __ _ _ __   __| |___| |__   __ _| | _____  ___         |
#   |       | '_ \ / _` | '_ \ / _` / __| '_ \ / _` | |/ / _ \/ __|        |
#   |       | | | | (_| | | | | (_| \__ \ | | | (_| |   <  __/\__ \        |
#   |       |_| |_|\__,_|_| |_|\__,_|___/_| |_|\__,_|_|\_\___||___/        |
#   |                                                                      |
#   '----------------------------------------------------------------------'

_aws_elbv2_network_tls_types = [
    "ClientTLSNegotiationErrorCount",
    "TargetTLSNegotiationErrorCount",
]


def check_aws_elbv2_network_tls_handshakes(item, params, parsed):
    return check_aws_metrics(
        [
            MetricInfo(
                metric_val=parsed.get(cw_metric_name),
                metric_name="aws_failed_tls_%s_handshake" % info_name.lower(),
                info_name=info_name,
                human_readable_func=aws_get_counts_rate_human_readable,
            )
            for cw_metric_name, info_name in zip(_aws_elbv2_network_tls_types, ["Client", "Target"])
        ]
    )


def discover_aws_elbv2_network_tls_handshakes(p):
    return inventory_aws_generic_single(p, _aws_elbv2_network_tls_types, requirement=any)


check_info["aws_elbv2_network.tls_handshakes"] = LegacyCheckDefinition(
    name="aws_elbv2_network_tls_handshakes",
    service_name="AWS/NetworkELB TLS Handshakes",
    sections=["aws_elbv2_network"],
    discovery_function=discover_aws_elbv2_network_tls_handshakes,
    check_function=check_aws_elbv2_network_tls_handshakes,
)

# .
#   .--RST packets---------------------------------------------------------.
#   |        ____  ____ _____                    _        _                |
#   |       |  _ \/ ___|_   _|  _ __   __ _  ___| | _____| |_ ___          |
#   |       | |_) \___ \ | |   | '_ \ / _` |/ __| |/ / _ \ __/ __|         |
#   |       |  _ < ___) || |   | |_) | (_| | (__|   <  __/ |_\__ \         |
#   |       |_| \_\____/ |_|   | .__/ \__,_|\___|_|\_\___|\__|___/         |
#   |                          |_|                                         |
#   '----------------------------------------------------------------------'

_aws_elbv2_network_rst_packets_types = [
    "TCP_Client_Reset_Count",
    "TCP_ELB_Reset_Count",
    "TCP_Target_Reset_Count",
]


def check_aws_elbv2_network_rst_packets(item, params, parsed):
    return check_aws_metrics(
        [
            MetricInfo(
                metric_val=parsed.get(cw_metric_name),
                metric_name="aws_%s" % key,
                info_name=info_name,
                human_readable_func=aws_get_counts_rate_human_readable,
            )
            for cw_metric_name, (info_name, key) in zip(
                _aws_elbv2_network_rst_packets_types,
                [
                    ("From client to target", "tcp_client_rst"),
                    ("Generated by load balancer", "tcp_elb_rst"),
                    ("From target to client", "tcp_target_rst"),
                ],
            )
        ]
    )


def discover_aws_elbv2_network_rst_packets(p):
    return inventory_aws_generic_single(p, _aws_elbv2_network_rst_packets_types, requirement=any)


check_info["aws_elbv2_network.rst_packets"] = LegacyCheckDefinition(
    name="aws_elbv2_network_rst_packets",
    service_name="AWS/NetworkELB Reset Packets",
    sections=["aws_elbv2_network"],
    discovery_function=discover_aws_elbv2_network_rst_packets,
    check_function=check_aws_elbv2_network_rst_packets,
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

_aws_elbv2_network_statistics_metric_names = [
    "ProcessedBytes",
    "ProcessedBytes_TLS",
]


def check_aws_elbv2_network_statistics(item, params, parsed):
    return check_aws_metrics(
        [
            MetricInfo(
                metric_val=parsed.get(cw_metric_name),
                metric_name="aws_%s" % key,
                info_name=info_name,
                human_readable_func=aws_get_bytes_rate_human_readable,
            )
            for cw_metric_name, (info_name, key) in zip(
                _aws_elbv2_network_statistics_metric_names,
                [
                    ("Processed bytes", "proc_bytes"),
                    ("Processed bytes TLS", "proc_bytes_tls"),
                ],
            )
        ]
    )


def discover_aws_elbv2_network_statistics(p):
    return inventory_aws_generic_single(
        p, _aws_elbv2_network_statistics_metric_names, requirement=any
    )


check_info["aws_elbv2_network.statistics"] = LegacyCheckDefinition(
    name="aws_elbv2_network_statistics",
    service_name="AWS/NetworkELB Statistics",
    sections=["aws_elbv2_network"],
    discovery_function=discover_aws_elbv2_network_statistics,
    check_function=check_aws_elbv2_network_statistics,
)
