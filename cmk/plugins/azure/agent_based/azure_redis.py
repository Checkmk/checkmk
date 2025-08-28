#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    render,
    Result,
    Service,
    State,
)
from cmk.agent_based.v2 import (
    check_levels as check_levels_v2,
)
from cmk.plugins.lib.azure import (
    create_check_metrics_function_single,
    create_discover_by_metrics_function_single,
    get_service_labels_from_resource_tags,
    MetricData,
    parse_resources,
    Section,
)

agent_section_azure_redis = AgentSection(name="azure_redis", parse_function=parse_resources)


def discover_azure_redis(section: Section) -> DiscoveryResult:
    for item, resource in section.items():
        yield Service(item=item, labels=get_service_labels_from_resource_tags(resource.tags))


def check_azure_redis(item: str, section: Section) -> CheckResult:
    if (resource := section.get(item)) is None:
        raise IgnoreResultsError("Data not present at the moment")
    # TODO: Maybe something more than location here... but for now...
    yield Result(state=State.OK, summary=f"Location: {resource.location}")


check_plugin_azure_redis = CheckPlugin(
    name="azure_redis",
    sections=["azure_redis"],
    service_name="Azure/Redis %s",
    discovery_function=discover_azure_redis,
    check_function=check_azure_redis,
)


check_plugin_azure_redis_connections = CheckPlugin(
    name="azure_redis_connections",
    sections=["azure_redis"],
    service_name="Azure/Redis connections",
    discovery_function=create_discover_by_metrics_function_single(
        "maximum_allconnectedclients",
        "maximum_allConnectionsCreatedPerSecond",
        "maximum_allConnectionsClosedPerSecond",
    ),
    check_function=create_check_metrics_function_single(
        [
            MetricData(
                "maximum_allconnectedclients",
                "azure_redis_clients_connected",
                "Connected clients",
                str,
                upper_levels_param="connected_clients",
            ),
            MetricData(
                "maximum_allConnectionsCreatedPerSecond",
                "azure_redis_created_connection_rate",
                "Created",
                lambda x: f"{x}/s",
                upper_levels_param="created_connections",
            ),
            MetricData(
                "maximum_allConnectionsClosedPerSecond",
                "azure_redis_closed_connection_rate",
                "Closed",
                lambda x: f"{x}/s",
            ),
        ],
        check_levels=check_levels_v2,  # Force v2 so default params work without migration params
    ),
    check_ruleset_name="azure_redis_connections",
    check_default_parameters={
        "connected_clients": ("fixed", (200, 250)),
        "created_connections": ("no_levels", None),
    },
)


check_plugin_azure_cpu_utilization = CheckPlugin(
    name="azure_redis_cpu_utilization",
    sections=["azure_redis"],
    service_name="Azure/Redis CPU utilization",
    discovery_function=create_discover_by_metrics_function_single(
        "maximum_allpercentprocessortime",
    ),
    check_function=create_check_metrics_function_single(
        [
            MetricData(
                "maximum_allpercentprocessortime",
                "util",
                "Total CPU",
                render.percent,
                upper_levels_param="connected_clients",
            ),
        ],
        check_levels=check_levels_v2,
    ),
    check_ruleset_name="azure_redis_cpu_utilization",
    check_default_parameters={
        "cpu_utilization": ("fixed", (70.0, 80.0)),
    },
)
