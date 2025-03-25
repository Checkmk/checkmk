#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v1 import check_levels  # we can only use v2 after migrating the ruleset!
from cmk.agent_based.v2 import (
    AgentSection,
    # check_levels,
    CheckPlugin,
    render,
)
from cmk.plugins.lib.azure import (
    CheckFunction,
    create_check_metrics_function,
    create_discover_by_metrics_function,
    MetricData,
    parse_resources,
)


def create_check_azure_storage() -> CheckFunction:
    return create_check_metrics_function(
        [
            MetricData(
                "total_UsedCapacity",
                "used_space",
                "Used capacity",
                render.bytes,
                upper_levels_param="used_capacity_levels",
            )
        ],
        check_levels=check_levels,
    )


agent_section_azure_storageaccounts = AgentSection(
    name="azure_storageaccounts", parse_function=parse_resources
)
check_plugin_azure_storageaccounts = CheckPlugin(
    name="azure_storageaccounts",
    service_name="Storage %s account",
    discovery_function=create_discover_by_metrics_function("total_UsedCapacity"),
    check_function=create_check_azure_storage(),
    check_ruleset_name="azure_storageaccounts",
    check_default_parameters={},
)


FLOW_METRICS = {
    "total_Ingress": render.bytes,
    "total_Egress": render.bytes,
    "total_Transactions": lambda x: str(int(x)),
}


def create_check_azure_storageaccounts_flow() -> CheckFunction:
    return create_check_metrics_function(
        [
            MetricData(
                metric_key,
                metric_key[6:].lower(),
                metric_key[6:].title(),
                render_func,
                upper_levels_param=f"{metric_key[6:].lower()}_levels",
            )
            for metric_key, render_func in FLOW_METRICS.items()
        ],
        check_levels=check_levels,
    )


check_plugin_azure_storageaccounts_flow = CheckPlugin(
    name="azure_storageaccounts_flow",
    service_name="Storage %s flow",
    sections=["azure_storageaccounts"],
    discovery_function=create_discover_by_metrics_function(*FLOW_METRICS.keys()),
    check_function=create_check_azure_storageaccounts_flow(),
    check_ruleset_name="azure_storageaccounts",
    check_default_parameters={},
)


def render_latency(value: float) -> str:
    return f"{int(value)} ms"


PERFORMANCE_METRICS = {
    "average_SuccessServerLatency": (
        "server_latency",
        "Success server latency",
        render_latency,
        "server_latency_levels",
        "",
    ),
    "average_SuccessE2ELatency": (
        "e2e_latency",
        "End-to-end server latency",
        render_latency,
        "e2e_latency_levels",
        "",
    ),
    "average_Availability": (
        "availability",
        "Availability",
        render.percent,
        "",
        "availability_levels",
    ),
}


def create_check_azure_storageaccounts_performance() -> CheckFunction:
    return create_check_metrics_function(
        [
            MetricData(
                metric_key,
                cmk_key,
                displ,
                render_func,
                upper_levels_param=upper_levels,
                lower_levels_param=lower_levels,
            )
            for metric_key, (
                cmk_key,
                displ,
                render_func,
                upper_levels,
                lower_levels,
            ) in PERFORMANCE_METRICS.items()
        ],
        check_levels=check_levels,
    )


check_plugin_azure_storageaccounts_performance = CheckPlugin(
    name="azure_storageaccounts_performance",
    service_name="Storage %s performance",
    sections=["azure_storageaccounts"],
    discovery_function=create_discover_by_metrics_function(*PERFORMANCE_METRICS.keys()),
    check_function=create_check_azure_storageaccounts_performance(),
    check_ruleset_name="azure_storageaccounts",
    check_default_parameters={},
)
