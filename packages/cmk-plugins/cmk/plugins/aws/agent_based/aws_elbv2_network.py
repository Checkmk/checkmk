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
    check_aws_metrics,
    discover_aws_generic_single,
    extract_aws_metrics_by_labels,
    parse_aws,
)

Section = Mapping[str, float]


def parse_aws_elbv2_network(string_table: StringTable) -> Section:
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


def check_aws_elbv2_network_lcu(params: Mapping[str, Any], section: Section) -> CheckResult:
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


def discover_aws_elbv2_network(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(section, ["ConsumedLCUs"])


agent_section_aws_elbv2_network = AgentSection(
    name="aws_elbv2_network",
    parse_function=parse_aws_elbv2_network,
)


check_plugin_aws_elbv2_network = CheckPlugin(
    name="aws_elbv2_network",
    service_name="AWS/NetworkELB LCUs",
    discovery_function=discover_aws_elbv2_network,
    check_function=check_aws_elbv2_network_lcu,
    check_ruleset_name="aws_elbv2_lcu",
    check_default_parameters={},
)


#   .--connections---------------------------------------------------------.

_aws_elbv2_network_connection_types = [
    "ActiveFlowCount",
    "ActiveFlowCount_TLS",
    "NewFlowCount",
    "NewFlowCount_TLS",
]


def check_aws_elbv2_network_connections(section: Section) -> CheckResult:
    yield from check_aws_metrics(
        [
            AWSMetric(
                value=value,
                name=f"aws_{key}_connections",
                label=info_name,
                render_func=aws_get_counts_rate_human_readable,
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
            if (value := section.get(cw_metric_name)) is not None
        ]
    )


def discover_aws_elbv2_network_connections(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(
        section, _aws_elbv2_network_connection_types, requirement=any
    )


check_plugin_aws_elbv2_network_connections = CheckPlugin(
    name="aws_elbv2_network_connections",
    service_name="AWS/NetworkELB Connections",
    sections=["aws_elbv2_network"],
    discovery_function=discover_aws_elbv2_network_connections,
    check_function=check_aws_elbv2_network_connections,
)


#   .--TLS handshakes------------------------------------------------------.

_aws_elbv2_network_tls_types = [
    "ClientTLSNegotiationErrorCount",
    "TargetTLSNegotiationErrorCount",
]


def check_aws_elbv2_network_tls_handshakes(section: Section) -> CheckResult:
    yield from check_aws_metrics(
        [
            AWSMetric(
                value=value,
                name=f"aws_failed_tls_{info_name.lower()}_handshake",
                label=info_name,
                render_func=aws_get_counts_rate_human_readable,
            )
            for cw_metric_name, info_name in zip(_aws_elbv2_network_tls_types, ["Client", "Target"])
            if (value := section.get(cw_metric_name)) is not None
        ]
    )


def discover_aws_elbv2_network_tls_handshakes(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(section, _aws_elbv2_network_tls_types, requirement=any)


check_plugin_aws_elbv2_network_tls_handshakes = CheckPlugin(
    name="aws_elbv2_network_tls_handshakes",
    service_name="AWS/NetworkELB TLS Handshakes",
    sections=["aws_elbv2_network"],
    discovery_function=discover_aws_elbv2_network_tls_handshakes,
    check_function=check_aws_elbv2_network_tls_handshakes,
)


#   .--RST packets---------------------------------------------------------.

_aws_elbv2_network_rst_packets_types = [
    "TCP_Client_Reset_Count",
    "TCP_ELB_Reset_Count",
    "TCP_Target_Reset_Count",
]


def check_aws_elbv2_network_rst_packets(section: Section) -> CheckResult:
    yield from check_aws_metrics(
        [
            AWSMetric(
                value=value,
                name=f"aws_{key}",
                label=info_name,
                render_func=aws_get_counts_rate_human_readable,
            )
            for cw_metric_name, (info_name, key) in zip(
                _aws_elbv2_network_rst_packets_types,
                [
                    ("From client to target", "tcp_client_rst"),
                    ("Generated by load balancer", "tcp_elb_rst"),
                    ("From target to client", "tcp_target_rst"),
                ],
            )
            if (value := section.get(cw_metric_name)) is not None
        ]
    )


def discover_aws_elbv2_network_rst_packets(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(
        section, _aws_elbv2_network_rst_packets_types, requirement=any
    )


check_plugin_aws_elbv2_network_rst_packets = CheckPlugin(
    name="aws_elbv2_network_rst_packets",
    service_name="AWS/NetworkELB Reset Packets",
    sections=["aws_elbv2_network"],
    discovery_function=discover_aws_elbv2_network_rst_packets,
    check_function=check_aws_elbv2_network_rst_packets,
)


#   .--statistics----------------------------------------------------------.

_aws_elbv2_network_statistics_metric_names = [
    "ProcessedBytes",
    "ProcessedBytes_TLS",
]


def check_aws_elbv2_network_statistics(section: Section) -> CheckResult:
    yield from check_aws_metrics(
        [
            AWSMetric(
                value=value,
                name=f"aws_{key}",
                label=info_name,
                render_func=aws_get_bytes_rate_human_readable,
            )
            for cw_metric_name, (info_name, key) in zip(
                _aws_elbv2_network_statistics_metric_names,
                [
                    ("Processed bytes", "proc_bytes"),
                    ("Processed bytes TLS", "proc_bytes_tls"),
                ],
            )
            if (value := section.get(cw_metric_name)) is not None
        ]
    )


def discover_aws_elbv2_network_statistics(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic_single(
        section, _aws_elbv2_network_statistics_metric_names, requirement=any
    )


check_plugin_aws_elbv2_network_statistics = CheckPlugin(
    name="aws_elbv2_network_statistics",
    service_name="AWS/NetworkELB Statistics",
    sections=["aws_elbv2_network"],
    discovery_function=discover_aws_elbv2_network_statistics,
    check_function=check_aws_elbv2_network_statistics,
)
