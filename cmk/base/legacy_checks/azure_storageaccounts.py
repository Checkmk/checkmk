#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Literal

from cmk.base.check_legacy_includes.azure import (
    check_azure_metric,
    discover_azure_by_metrics,
    get_data_or_go_stale,
)

from cmk.agent_based.legacy.v0_unstable import (
    LegacyCheckDefinition,
    LegacyCheckResult,
)
from cmk.agent_based.v2 import DiscoveryResult, Service
from cmk.plugins.lib.azure import (
    get_service_labels_from_resource_tags,
    iter_resource_attributes,
    parse_resources,
    Resource,
)

check_info = {}

Section = Mapping[str, Resource]


def check_azure_storageaccounts(
    item: str,
    params: Mapping[Literal["used_capacity_levels"], tuple[float, float] | None],
    section: Section,
) -> LegacyCheckResult:
    resource = get_data_or_go_stale(item, section)
    iter_attrs = iter_resource_attributes(resource, include_keys=("kind", "location"))
    # kind first
    try:
        yield 0, "%s: %s" % next(iter_attrs)
    except StopIteration:
        pass

    levels = params.get("used_capacity_levels")
    mcheck = check_azure_metric(
        resource, "total_UsedCapacity", "used_space", "Used capacity", levels=levels
    )
    if mcheck:
        yield mcheck

    for kv_pair in iter_attrs:
        yield 0, "%s: %s" % kv_pair


def discover_azure_storageaccounts(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=item, labels=get_service_labels_from_resource_tags(resource.tags))
        for item, resource in section.items()
    )


check_info["azure_storageaccounts"] = LegacyCheckDefinition(
    name="azure_storageaccounts",
    parse_function=parse_resources,
    service_name="Storage %s account",
    discovery_function=discover_azure_storageaccounts,
    check_function=check_azure_storageaccounts,
    check_ruleset_name="azure_storageaccounts",
    check_default_parameters={},
    # metrics description:
    # https://docs.microsoft.com/en-US/azure/monitoring-and-diagnostics/monitoring-supported-metrics#microsoftstoragestorageaccounts
    # 'ingress_levels': tuple [B]
    # 'egress_levels': tuple [B]
    # 'used_capacity_levels': tuple [B]
    # 'server_latency_levels': tuple [ms]
    # 'e2e_latency_levels': tuple [ms]
    # 'transactions_levels': tuple int
    # 'availablility_levels': tuple float
    #     The percentage of availability for the storage service or the specified API operation.
    #     Availability is calculated by taking the TotalBillableRequests value and dividing it
    #     by the number of applicable requests, including those that produced unexpected errors.
    #     All unexpected errors result in reduced availability for the storage service or the
    #     specified API operation.,
)


def check_azure_storageaccounts_flow(
    item: str, params: Mapping[str, tuple[float, float] | None], section: Section
) -> LegacyCheckResult:
    resource = get_data_or_go_stale(item, section)
    for metric_key in ("total_Ingress", "total_Egress", "total_Transactions"):
        cmk_key = metric_key[6:].lower()
        displ = cmk_key.title()
        levels = params.get("%s_levels" % cmk_key)
        mcheck = check_azure_metric(resource, metric_key, cmk_key, displ, levels=levels)
        if mcheck:
            yield mcheck


check_info["azure_storageaccounts.flow"] = LegacyCheckDefinition(
    name="azure_storageaccounts_flow",
    service_name="Storage %s flow",
    sections=["azure_storageaccounts"],
    discovery_function=discover_azure_by_metrics(
        "total_Ingress", "total_Egress", "total_Transactions"
    ),
    check_function=check_azure_storageaccounts_flow,
    check_ruleset_name="azure_storageaccounts",
    check_default_parameters={},
    # metrics description:
    # https://docs.microsoft.com/en-US/azure/monitoring-and-diagnostics/monitoring-supported-metrics#microsoftstoragestorageaccounts
    # 'ingress_levels': tuple [B]
    # 'egress_levels': tuple [B]
    # 'used_capacity_levels': tuple [B]
    # 'server_latency_levels': tuple [ms]
    # 'e2e_latency_levels': tuple [ms]
    # 'transactions_levels': tuple int
    # 'availablility_levels': tuple float
    #     The percentage of availability for the storage service or the specified API operation.
    #     Availability is calculated by taking the TotalBillableRequests value and dividing it
    #     by the number of applicable requests, including those that produced unexpected errors.
    #     All unexpected errors result in reduced availability for the storage service or the
    #     specified API operation.,
)


def check_azure_storageaccounts_performance(
    item: str, params: Mapping[str, tuple[float, float]], section: Section
) -> LegacyCheckResult:
    resource = get_data_or_go_stale(item, section)
    for key, cmk_key, displ in (
        ("average_SuccessServerLatency", "server_latency", "Success server latency"),
        ("average_SuccessE2ELatency", "e2e_latency", "End-to-end server latency"),
        ("average_Availability", "availability", "Availability"),
    ):
        levels = params.get("%s_levels" % cmk_key)
        mcheck = check_azure_metric(resource, key, cmk_key, displ, levels=levels)
        if mcheck:
            yield mcheck


check_info["azure_storageaccounts.performance"] = LegacyCheckDefinition(
    name="azure_storageaccounts_performance",
    service_name="Storage %s performance",
    sections=["azure_storageaccounts"],
    discovery_function=discover_azure_by_metrics(
        "average_SuccessServerLatency", "average_SuccessE2ELatency", "average_Availability"
    ),
    check_function=check_azure_storageaccounts_performance,
    check_ruleset_name="azure_storageaccounts",
    check_default_parameters={},
    # metrics description:
    # https://docs.microsoft.com/en-US/azure/monitoring-and-diagnostics/monitoring-supported-metrics#microsoftstoragestorageaccounts
    # 'ingress_levels': tuple [B]
    # 'egress_levels': tuple [B]
    # 'used_capacity_levels': tuple [B]
    # 'server_latency_levels': tuple [ms]
    # 'e2e_latency_levels': tuple [ms]
    # 'transactions_levels': tuple int
    # 'availablility_levels': tuple float
    #     The percentage of availability for the storage service or the specified API operation.
    #     Availability is calculated by taking the TotalBillableRequests value and dividing it
    #     by the number of applicable requests, including those that produced unexpected errors.
    #     All unexpected errors result in reduced availability for the storage service or the
    #     specified API operation.,
)
