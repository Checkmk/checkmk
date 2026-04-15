#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v1.type_defs import CheckResult
from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    DiscoveryResult,
    IgnoreResultsError,
    InventoryPlugin,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.azure_v2.agent_based.lib import (
    check_resource_metrics,
    create_inventory_function,
    get_service_labels_from_resource_tags,
    MetricData,
    parse_resource,
    Resource,
)

inventory_plugin_azure_storageaccounts = InventoryPlugin(
    name="azure_v2_storageaccounts",
    inventory_function=create_inventory_function(),
)


def _check_metrics_with_inactivity_fallback(
    resource: Resource,
    params: Mapping[str, Any],
    metrics_data: Sequence[MetricData],
) -> CheckResult:
    """Check metrics individually and yield inactivity message only if all fail."""
    all_failed = True
    for metric in metrics_data:
        try:
            yield from check_resource_metrics(
                resource.id,
                resource.metrics,
                params,
                [metric],
                check_levels=check_levels,
            )
            all_failed = False
        except IgnoreResultsError:
            pass

    if all_failed:
        yield Result(
            state=State.OK,
            summary="No data in the Azure API response due to inactivity on the storage account.",
        )


def discover_azure_storageaccounts(section: Resource) -> DiscoveryResult:
    yield Service(labels=get_service_labels_from_resource_tags(section.tags))


def check_azure_storage(params: Mapping[str, Any], section: Resource) -> CheckResult:
    yield from _check_metrics_with_inactivity_fallback(
        section,
        params,
        [
            MetricData(
                "total_UsedCapacity",
                "used_space",
                "Used capacity",
                render.bytes,
                upper_levels_param="used_capacity_levels",
            )
        ],
    )


agent_section_azure_storageaccounts = AgentSection(
    name="azure_v2_storageaccounts", parse_function=parse_resource
)
check_plugin_azure_storageaccounts = CheckPlugin(
    name="azure_v2_storageaccounts",
    service_name="Azure/Storage account",
    sections=["azure_v2_storageaccounts"],
    discovery_function=discover_azure_storageaccounts,
    check_function=check_azure_storage,
    check_ruleset_name="azure_v2_storageaccounts_usage",
    check_default_parameters={
        "used_capacity_levels": (
            "fixed",
            (
                # B   KiB    MiB    GiB    TiB
                1 * 1024 * 1024 * 1024 * 1024 * 50,  # 50 TiB
                1 * 1024 * 1024 * 1024 * 1024 * 500,  # 500 TiB
            ),
        )
    },
)


FLOW_METRICS = {
    "total_Ingress": render.bytes,
    "total_Egress": render.bytes,
    "total_Transactions": lambda x: str(int(x)),
}


def check_azure_storageaccounts_flow(params: Mapping[str, Any], section: Resource) -> CheckResult:
    yield from _check_metrics_with_inactivity_fallback(
        section,
        params,
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
    )


check_plugin_azure_storageaccounts_flow = CheckPlugin(
    name="azure_v2_storageaccounts_flow",
    service_name="Azure/Storage flow",
    sections=["azure_v2_storageaccounts"],
    discovery_function=discover_azure_storageaccounts,
    check_function=check_azure_storageaccounts_flow,
    check_ruleset_name="azure_v2_storageaccounts_flow",
    check_default_parameters={
        "ingress_levels": ("no_levels", None),
        "egress_levels": ("no_levels", None),
        "transactions_levels": ("fixed", (8, 10)),
    },
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


def check_azure_storageaccounts_performance(
    params: Mapping[str, Any], section: Resource
) -> CheckResult:
    yield from _check_metrics_with_inactivity_fallback(
        section,
        params,
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
    )


check_plugin_azure_storageaccounts_performance = CheckPlugin(
    name="azure_v2_storageaccounts_performance",
    service_name="Azure/Storage performance",
    sections=["azure_v2_storageaccounts"],
    discovery_function=discover_azure_storageaccounts,
    check_function=check_azure_storageaccounts_performance,
    check_ruleset_name="azure_v2_storageaccounts_performance",
    check_default_parameters={
        "server_latency_levels": ("fixed", (701, 1001)),
        "e2e_latency_levels": ("fixed", (701, 1001)),
        "availability_levels": ("fixed", (99.8, 99.0)),
    },
)
