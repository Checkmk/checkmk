#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.lib.azure import (
    CheckFunction,
    create_check_metrics_function,
    create_discover_by_metrics_function,
    get_service_labels_from_resource_tags,
    iter_resource_attributes,
    MetricData,
    parse_resources,
    Section,
)

# https://www.unigma.com/2016/07/11/best-practices-for-monitoring-microsoft-azure/


def create_check_azure_databases_storage() -> CheckFunction:
    return create_check_metrics_function(
        [
            MetricData(
                "average_storage_percent",
                "storage_percent",
                "Storage",
                render.percent,
                upper_levels_param="storage_percent_levels",
            )
        ]
    )


check_plugin_azure_databases_storage = CheckPlugin(
    name="azure_databases_storage",
    service_name="DB %s Storage",
    sections=["azure_databases"],
    discovery_function=create_discover_by_metrics_function("average_storage_percent"),
    check_function=create_check_azure_databases_storage(),
    check_ruleset_name="azure_databases",
    check_default_parameters={
        "storage_percent_levels": (85.0, 95.0),
        "cpu_percent_levels": (85.0, 95.0),
        "dtu_percent_levels": (85.0, 95.0),
        "deadlocks_levels": None,
    },
)


def create_check_azure_databases_deadlock() -> CheckFunction:
    return create_check_metrics_function(
        [
            MetricData(
                "average_deadlock",
                "deadlocks",
                "Deadlocks",
                lambda x: str(x),
                upper_levels_param="deadlocks_levels",
            )
        ]
    )


check_plugin_azure_databases_deadlock = CheckPlugin(
    name="azure_databases_deadlock",
    service_name="DB %s Deadlocks",
    sections=["azure_databases"],
    discovery_function=create_discover_by_metrics_function("average_deadlock"),
    check_function=create_check_azure_databases_deadlock(),
    check_ruleset_name="azure_databases",
    check_default_parameters={
        "storage_percent_levels": (85.0, 95.0),
        "cpu_percent_levels": (85.0, 95.0),
        "dtu_percent_levels": (85.0, 95.0),
        "deadlocks_levels": None,
    },
)


def create_check_azure_databases_cpu() -> CheckFunction:
    return create_check_metrics_function(
        [
            MetricData(
                "average_cpu_percent",
                "util",
                "CPU",
                render.percent,
                upper_levels_param="cpu_percent_levels",
            )
        ]
    )


check_plugin_azure_databases_cpu = CheckPlugin(
    name="azure_databases_cpu",
    service_name="DB %s CPU",
    sections=["azure_databases"],
    discovery_function=create_discover_by_metrics_function("average_cpu_percent"),
    check_function=create_check_azure_databases_cpu(),
    check_ruleset_name="azure_databases",
    check_default_parameters={
        "storage_percent_levels": (85.0, 95.0),
        "cpu_percent_levels": (85.0, 95.0),
        "dtu_percent_levels": (85.0, 95.0),
        "deadlocks_levels": None,
    },
)


def create_check_azure_databases_dtu() -> CheckFunction:
    return create_check_metrics_function(
        [
            MetricData(
                "average_dtu_consumption_percent",
                "dtu_percent",
                "Database throughput units",
                render.percent,
                upper_levels_param="dtu_percent_levels",
            )
        ]
    )


check_plugin_azure_databases_dtu = CheckPlugin(
    name="azure_databases_dtu",
    service_name="DB %s DTU",
    sections=["azure_databases"],
    discovery_function=create_discover_by_metrics_function("average_dtu_consumption_percent"),
    check_function=create_check_azure_databases_dtu(),
    check_ruleset_name="azure_databases",
    check_default_parameters={
        "storage_percent_levels": (85.0, 95.0),
        "cpu_percent_levels": (85.0, 95.0),
        "dtu_percent_levels": (85.0, 95.0),
        "deadlocks_levels": None,
    },
)


def create_check_azure_databases_connections() -> CheckFunction:
    return create_check_metrics_function(
        [
            MetricData(
                "average_connection_successful",
                "connections",
                "Successful connections",
                lambda x: str(x),
                upper_levels_param="connections_levels",
            ),
            MetricData(
                "average_connection_failed",
                "connections_failed_rate",
                "Failed connections",
                lambda x: str(x),
                upper_levels_param="connections_failed_rate_levels",
            ),
        ]
    )


check_plugin_azure_databases_connections = CheckPlugin(
    name="azure_databases_connections",
    service_name="DB %s Connections",
    sections=["azure_databases"],
    discovery_function=create_discover_by_metrics_function(
        "average_connection_successful", "average_connection_failed"
    ),
    check_function=create_check_azure_databases_connections(),
    # TODO: Use the actual ruleset defining connection limits
    check_ruleset_name="azure_databases",
    check_default_parameters={
        "storage_percent_levels": (85.0, 95.0),
        "cpu_percent_levels": (85.0, 95.0),
        "dtu_percent_levels": (85.0, 95.0),
        "deadlocks_levels": None,
    },
)


def check_azure_databases(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    resource = section.get(item)
    if not resource:
        return
    for k, v in iter_resource_attributes(resource):
        yield Result(state=State.OK, summary=f"{k}: {v}")


def discover_azure_databases(section: Any) -> DiscoveryResult:
    yield from (
        Service(
            item=item,
            labels=get_service_labels_from_resource_tags(resource.tags),
        )
        for item, resource in section.items()
    )


agent_section_azure_databases = AgentSection(name="azure_databases", parse_function=parse_resources)
check_plugin_azure_databases = CheckPlugin(
    name="azure_databases",
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
