#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="arg-type"

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.azure import (
    check_azure_metric,
    discover_azure_by_metrics,
    get_data_or_go_stale,
    iter_resource_attributes,
    parse_resources,
)
from cmk.base.config import check_info


@get_data_or_go_stale
def check_azure_storageaccounts(_item, params, resource):
    iter_attrs = iter_resource_attributes(resource, include_keys=("kind", "location"))
    # kind first
    try:
        yield 0, "%s: %s" % next(iter_attrs)
    except StopIteration:
        pass

    levels = params.get("used_capacity_levels", (None, None))
    mcheck = check_azure_metric(
        resource, "total_UsedCapacity", "used_space", "Used capacity", levels=levels
    )
    if mcheck:
        yield mcheck

    for kv_pair in iter_attrs:
        yield 0, "%s: %s" % kv_pair


def discover_azure_storageaccounts(section):
    yield from ((item, {}) for item in section)


check_info["azure_storageaccounts"] = LegacyCheckDefinition(
    parse_function=parse_resources,
    service_name="Storage %s account",
    discovery_function=discover_azure_storageaccounts,
    check_function=check_azure_storageaccounts,
    check_ruleset_name="azure_storageaccounts",
    check_default_parameters={}
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


@get_data_or_go_stale
def check_azure_storageaccounts_flow(_item, params, resource):
    for metric_key in ("total_Ingress", "total_Egress", "total_Transactions"):
        cmk_key = metric_key[6:].lower()
        displ = cmk_key.title()
        levels = params.get("%s_levels" % cmk_key, (None, None))
        mcheck = check_azure_metric(resource, metric_key, cmk_key, displ, levels=levels)
        if mcheck:
            yield mcheck


check_info["azure_storageaccounts.flow"] = LegacyCheckDefinition(
    service_name="Storage %s flow",
    discovery_function=discover_azure_by_metrics(
        "total_Ingress", "total_Egress", "total_Transactions"
    ),
    check_function=check_azure_storageaccounts_flow,
    check_ruleset_name="azure_storageaccounts",
    check_default_parameters={}
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


@get_data_or_go_stale
def check_azure_storageaccounts_performance(_item, params, resource):
    for key, cmk_key, displ in (
        ("average_SuccessServerLatency", "server_latency", "Success server latency"),
        ("average_SuccessE2ELatency", "e2e_latency", "End-to-end server latency"),
        ("average_Availability", "availability", "Availability"),
    ):
        levels = params.get("%s_levels" % cmk_key, (None, None))
        mcheck = check_azure_metric(resource, key, cmk_key, displ, levels=levels)
        if mcheck:
            yield mcheck


check_info["azure_storageaccounts.performance"] = LegacyCheckDefinition(
    service_name="Storage %s performance",
    discovery_function=discover_azure_by_metrics(
        "average_SuccessServerLatency", "average_SuccessE2ELatency", "average_Availability"
    ),
    check_function=check_azure_storageaccounts_performance,
    check_ruleset_name="azure_storageaccounts",
    check_default_parameters={}
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
