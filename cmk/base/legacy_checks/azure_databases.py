#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.azure import (
    check_azure_metric,
    discover_azure_by_metrics,
    get_data_or_go_stale,
)
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import render, Service
from cmk.plugins.lib.azure import (
    get_service_labels_from_resource_tags,
    iter_resource_attributes,
    parse_resources,
)

check_info = {}

# https://www.unigma.com/2016/07/11/best-practices-for-monitoring-microsoft-azure/


def check_azure_databases_storage(item, params, section):
    resource = get_data_or_go_stale(item, section)
    cmk_key = "storage_percent"
    levels = params.get("%s_levels" % cmk_key)
    mcheck = check_azure_metric(
        resource, "average_storage_percent", cmk_key, "Storage", levels=levels
    )
    if mcheck and len(mcheck) == 3:
        state, text, *perf = mcheck
        abs_storage_metric = resource.metrics.get("average_storage")
        if abs_storage_metric is not None:
            text += " (%s)" % render.bytes(abs_storage_metric.value)
        yield state, text, *perf


check_info["azure_databases.storage"] = LegacyCheckDefinition(
    name="azure_databases_storage",
    service_name="DB %s Storage",
    sections=["azure_databases"],
    discovery_function=discover_azure_by_metrics("average_storage_percent"),
    check_function=check_azure_databases_storage,
    check_ruleset_name="azure_databases",
    check_default_parameters={
        "storage_percent_levels": (85.0, 95.0),
        "cpu_percent_levels": (85.0, 95.0),
        "dtu_percent_levels": (85.0, 95.0),
        "deadlocks_levels": None,
    },
)


def check_azure_databases_deadlock(item, params, section):
    resource = get_data_or_go_stale(item, section)
    cmk_key = "deadlocks"
    levels = params.get("%s_levels" % cmk_key)
    mcheck = check_azure_metric(resource, "average_deadlock", cmk_key, "Deadlocks", levels=levels)
    if mcheck:
        yield mcheck


check_info["azure_databases.deadlock"] = LegacyCheckDefinition(
    name="azure_databases_deadlock",
    service_name="DB %s Deadlocks",
    sections=["azure_databases"],
    discovery_function=discover_azure_by_metrics("average_deadlock"),
    check_function=check_azure_databases_deadlock,
    check_ruleset_name="azure_databases",
    check_default_parameters={
        "storage_percent_levels": (85.0, 95.0),
        "cpu_percent_levels": (85.0, 95.0),
        "dtu_percent_levels": (85.0, 95.0),
        "deadlocks_levels": None,
    },
)


def check_azure_databases_cpu(item, params, section):
    resource = get_data_or_go_stale(item, section)
    metrics = resource.metrics

    cpu_percent = metrics.get("average_cpu_percent")
    util_params = {}
    if cpu_percent is not None:
        if "cpu_percent_levels" in params:
            util_params["levels"] = params["cpu_percent_levels"]
        yield from check_cpu_util(cpu_percent.value, util_params)


check_info["azure_databases.cpu"] = LegacyCheckDefinition(
    name="azure_databases_cpu",
    service_name="DB %s CPU",
    sections=["azure_databases"],
    discovery_function=discover_azure_by_metrics("average_cpu_percent"),
    check_function=check_azure_databases_cpu,
    check_ruleset_name="azure_databases",
    check_default_parameters={
        "storage_percent_levels": (85.0, 95.0),
        "cpu_percent_levels": (85.0, 95.0),
        "dtu_percent_levels": (85.0, 95.0),
        "deadlocks_levels": None,
    },
)


def check_azure_databases_dtu(item, params, section):
    resource = get_data_or_go_stale(item, section)
    cmk_key = "dtu_percent"
    levels = params.get("%s_levels" % cmk_key)
    mcheck = check_azure_metric(
        resource,
        "average_dtu_consumption_percent",
        cmk_key,
        "Database throughput units",
        levels=levels,
    )
    if mcheck:
        yield mcheck


check_info["azure_databases.dtu"] = LegacyCheckDefinition(
    name="azure_databases_dtu",
    service_name="DB %s DTU",
    sections=["azure_databases"],
    discovery_function=discover_azure_by_metrics("average_dtu_consumption_percent"),
    check_function=check_azure_databases_dtu,
    check_ruleset_name="azure_databases",
    check_default_parameters={
        "storage_percent_levels": (85.0, 95.0),
        "cpu_percent_levels": (85.0, 95.0),
        "dtu_percent_levels": (85.0, 95.0),
        "deadlocks_levels": None,
    },
)

_AZURE_CONNECTIONS_METRICS = (
    # metric key                      cmk key,                   display                       use_rate
    ("average_connection_successful", "connections", "Successful connections", False),
    ("average_connection_failed", "connections_failed_rate", "Rate of failed connections", True),
)


def check_azure_databases_connections(item, params, section):
    resource = get_data_or_go_stale(item, section)
    for key, cmk_key, displ, use_rate in _AZURE_CONNECTIONS_METRICS:
        levels = params.get("%s_levels" % cmk_key)
        mcheck = check_azure_metric(resource, key, cmk_key, displ, levels=levels, use_rate=use_rate)
        if mcheck:
            yield mcheck


check_info["azure_databases.connections"] = LegacyCheckDefinition(
    name="azure_databases_connections",
    service_name="DB %s Connections",
    sections=["azure_databases"],
    discovery_function=discover_azure_by_metrics(
        "average_connection_successful", "average_connection_failed"
    ),
    check_function=check_azure_databases_connections,
    check_ruleset_name="azure_databases",
    check_default_parameters={
        "storage_percent_levels": (85.0, 95.0),
        "cpu_percent_levels": (85.0, 95.0),
        "dtu_percent_levels": (85.0, 95.0),
        "deadlocks_levels": None,
    },
)


def check_azure_databases(item, _no_params, section):
    resource = get_data_or_go_stale(item, section)
    for k, v in iter_resource_attributes(resource):
        yield 0, f"{k}: {v}"


def discover_azure_databases(section):
    yield from (
        Service(
            item=item,
            labels=get_service_labels_from_resource_tags(resource.tags),
        )
        for item, resource in section.items()
    )


check_info["azure_databases"] = LegacyCheckDefinition(
    name="azure_databases",
    parse_function=parse_resources,
    service_name="DB %s",
    discovery_function=discover_azure_databases,
    check_function=check_azure_databases,
    check_ruleset_name="azure_databases",
    check_default_parameters={
        "storage_percent_levels": (85.0, 95.0),
        "cpu_percent_levels": (85.0, 95.0),
        "dtu_percent_levels": (85.0, 95.0),
        "deadlocks_levels": None,
    },
)
