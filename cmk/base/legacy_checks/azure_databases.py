#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import discover, get_bytes_human_readable, LegacyCheckDefinition
from cmk.base.check_legacy_includes.azure import (
    check_azure_metric,
    discover_azure_by_metrics,
    get_data_or_go_stale,
    iter_resource_attributes,
    parse_resources,
)
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.config import check_info, factory_settings

# https://www.unigma.com/2016/07/11/best-practices-for-monitoring-microsoft-azure/
factory_settings["azure_databases_default_levels"] = {
    "storage_percent_levels": (85.0, 95.0),
    "cpu_percent_levels": (85.0, 95.0),
    "dtu_percent_levels": (85.0, 95.0),
}


@get_data_or_go_stale
def check_azure_databases_storage(_item, params, resource):
    cmk_key = "storage_percent"
    levels = params.get("%s_levels" % cmk_key)
    mcheck = check_azure_metric(
        resource, "average_storage_percent", cmk_key, "Storage", levels=levels
    )
    if mcheck:
        state, text, perf = mcheck
        abs_storage_metric = resource.metrics.get("average_storage")
        if abs_storage_metric is not None:
            text += " (%s)" % get_bytes_human_readable(abs_storage_metric.value)
        yield state, text, perf


check_info["azure_databases.storage"] = LegacyCheckDefinition(
    discovery_function=discover_azure_by_metrics("average_storage_percent"),
    check_function=check_azure_databases_storage,
    service_name="DB %s Storage",
    default_levels_variable="azure_databases_default_levels",
    check_ruleset_name="azure_databases",
    check_default_parameters={
        "storage_percent_levels": (85.0, 95.0),
        "cpu_percent_levels": (85.0, 95.0),
        "dtu_percent_levels": (85.0, 95.0),
    },
)


@get_data_or_go_stale
def check_azure_databases_deadlock(_item, params, resource):
    cmk_key = "deadlocks"
    levels = params.get("%s_levels" % cmk_key)
    mcheck = check_azure_metric(resource, "average_deadlock", cmk_key, "Deadlocks", levels=levels)
    if mcheck:
        yield mcheck


check_info["azure_databases.deadlock"] = LegacyCheckDefinition(
    discovery_function=discover_azure_by_metrics("average_deadlock"),
    check_function=check_azure_databases_deadlock,
    service_name="DB %s Deadlocks",
    default_levels_variable="azure_databases_default_levels",
    check_ruleset_name="azure_databases",
    check_default_parameters={
        "storage_percent_levels": (85.0, 95.0),
        "cpu_percent_levels": (85.0, 95.0),
        "dtu_percent_levels": (85.0, 95.0),
    },
)


@get_data_or_go_stale
def check_azure_databases_cpu(_item, params, resource):
    metrics = resource.metrics

    cpu_percent = metrics.get("average_cpu_percent")
    util_params = {}
    if cpu_percent is not None:
        if "cpu_percent_levels" in params:
            util_params["levels"] = params["cpu_percent_levels"]
        for y in check_cpu_util(cpu_percent.value, util_params):
            yield y


check_info["azure_databases.cpu"] = LegacyCheckDefinition(
    discovery_function=discover_azure_by_metrics("average_cpu_percent"),
    check_function=check_azure_databases_cpu,
    service_name="DB %s CPU",
    default_levels_variable="azure_databases_default_levels",
    check_ruleset_name="azure_databases",
    check_default_parameters={
        "storage_percent_levels": (85.0, 95.0),
        "cpu_percent_levels": (85.0, 95.0),
        "dtu_percent_levels": (85.0, 95.0),
    },
)


@get_data_or_go_stale
def check_azure_databases_dtu(_item, params, resource):
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
    discovery_function=discover_azure_by_metrics("average_dtu_consumption_percent"),
    check_function=check_azure_databases_dtu,
    service_name="DB %s DTU",
    default_levels_variable="azure_databases_default_levels",
    check_ruleset_name="azure_databases",
    check_default_parameters={
        "storage_percent_levels": (85.0, 95.0),
        "cpu_percent_levels": (85.0, 95.0),
        "dtu_percent_levels": (85.0, 95.0),
    },
)

_AZURE_CONNECTIONS_METRICS = (
    # metric key                      cmk key,                   display                       use_rate
    ("average_connection_successful", "connections", "Successful connections", False),
    ("average_connection_failed", "connections_failed_rate", "Rate of failed connections", True),
)


@get_data_or_go_stale
def check_azure_databases_connections(_item, params, resource):
    for key, cmk_key, displ, use_rate in _AZURE_CONNECTIONS_METRICS:
        levels = params.get("%s_levels" % cmk_key)
        mcheck = check_azure_metric(resource, key, cmk_key, displ, levels=levels, use_rate=use_rate)
        if mcheck:
            yield mcheck


check_info["azure_databases.connections"] = LegacyCheckDefinition(
    discovery_function=discover_azure_by_metrics(
        "average_connection_successful", "average_connection_failed"
    ),
    check_function=check_azure_databases_connections,
    service_name="DB %s Connections",
    default_levels_variable="azure_databases_default_levels",
    check_ruleset_name="azure_databases",
    check_default_parameters={
        "storage_percent_levels": (85.0, 95.0),
        "cpu_percent_levels": (85.0, 95.0),
        "dtu_percent_levels": (85.0, 95.0),
    },
)


@get_data_or_go_stale
def check_azure_databases(_item, _no_params, resource):
    for k, v in iter_resource_attributes(resource):
        yield 0, "%s: %s" % (k, v)


check_info["azure_databases"] = LegacyCheckDefinition(
    parse_function=parse_resources,
    discovery_function=discover(),
    check_function=check_azure_databases,
    service_name="DB %s",
    default_levels_variable="azure_databases_default_levels",
    check_ruleset_name="azure_databases",
    check_default_parameters={
        "storage_percent_levels": (85.0, 95.0),
        "cpu_percent_levels": (85.0, 95.0),
        "dtu_percent_levels": (85.0, 95.0),
    },
)
