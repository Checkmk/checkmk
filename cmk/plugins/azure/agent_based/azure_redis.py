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
    InventoryPlugin,
    render,
    Result,
    Service,
    State,
)
from cmk.agent_based.v2 import check_levels as check_levels_v2
from cmk.plugins.lib.azure import (
    create_check_metrics_function_single,
    create_discover_by_metrics_function_single,
    get_service_labels_from_resource_tags,
    inventory_common_azure,
    MetricData,
    parse_resources,
    Section,
)

agent_section_azure_redis = AgentSection(name="azure_redis", parse_function=parse_resources)

inventory_plugin_azure_redis = InventoryPlugin(
    name="azure_redis",
    inventory_function=inventory_common_azure,
)


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


check_plugin_azure_redis_cpu_utilization = CheckPlugin(
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


check_plugin_azure_redis_cache_effectiveness = CheckPlugin(
    name="azure_redis_cache_effectiveness",
    sections=["azure_redis"],
    service_name="Azure/Redis Cache effectiveness",
    discovery_function=create_discover_by_metrics_function_single(
        "total_cachemissrate",
        "total_allcachehits",
        "total_allcachemisses",
    ),
    check_function=create_check_metrics_function_single(
        [
            MetricData(
                "total_cachemissrate",
                "azure_redis_cache_hit_ratio",
                "Hit ratio",
                render.percent,
                lower_levels_param="cache_hit_ratio",
                map_func=lambda x: 100.0 - x,  # Convert miss rate to hit rate
            ),
            MetricData(
                "total_allcachehits",
                "azure_redis_cache_hits",
                "Cache hits",
                str,
            ),
            MetricData(
                "total_allcachemisses",
                "azure_redis_cache_misses",
                "Cache misses",
                str,
            ),
            MetricData(
                "total_allgetcommands",
                "azure_redis_gets",
                "Gets",
                str,
                notice_only=True,
            ),
        ],
        check_levels=check_levels_v2,  # Force v2 so default params work without migration params
    ),
    check_ruleset_name="azure_redis_cache_effectiveness",
    check_default_parameters={
        "cache_hit_ratio": ("fixed", (85.0, 80.0)),
    },
)


check_plugin_azure_redis_memory = CheckPlugin(
    name="azure_redis_memory",
    sections=["azure_redis"],
    service_name="Azure/Redis Memory",
    discovery_function=create_discover_by_metrics_function_single(
        "total_allusedmemorypercentage",
        "total_allusedmemoryRss",
        "total_allevictedkeys",
        "total_allexpiredkeys",
    ),
    check_function=create_check_metrics_function_single(
        [
            MetricData(
                "total_allusedmemorypercentage",
                "azure_redis_memory_utilization",
                "Memory utilization",
                render.percent,
                upper_levels_param="memory_util",
            ),
            MetricData(
                "total_allusedmemory",
                "azure_redis_used_memory",
                "Used memory",
                render.bytes,
                notice_only=True,
            ),
            MetricData(
                "total_allusedmemoryRss",
                "azure_redis_used_memory_rss",
                "Used memory RSS",
                render.bytes,
                notice_only=True,
            ),
            MetricData(
                "total_allevictedkeys",
                "azure_redis_evicted_keys",
                "Evicted keys",
                str,
                upper_levels_param="evicted_keys",
            ),
            MetricData(
                "total_allexpiredkeys",
                "azure_redis_expired_keys",
                "Expired keys",
                str,
            ),
        ],
        check_levels=check_levels_v2,  # Force v2 so default params work without migration params
    ),
    check_ruleset_name="azure_redis_memory",
    check_default_parameters={
        "memory_util": ("fixed", (70.0, 80.0)),
        "evicted_keys": ("no_levels", None),
    },
)

check_plugin_azure_redis_latency = CheckPlugin(
    name="azure_redis_latency",
    sections=["azure_redis"],
    service_name="Azure/Redis Latency",
    discovery_function=create_discover_by_metrics_function_single(
        "average_LatencyP99",
        "average_cacheLatency",
    ),
    check_function=create_check_metrics_function_single(
        [
            MetricData(
                "average_LatencyP99",
                "azure_redis_latency_serverside",
                "Server-side",
                render.timespan,
                upper_levels_param="serverside_upper",
                map_func=lambda us: us / 1000000.0,  # render.timespan wants seconds, not microsec.
            ),
            MetricData(
                "average_cacheLatency",
                "azure_redis_latency_internode",
                "Cache internode",
                render.timespan,
                upper_levels_param="internode_upper",
                map_func=lambda us: us / 1000000.0,  # render.timespan wants seconds, not microsec.
            ),
        ],
        check_levels=check_levels_v2,  # Force v2 so default params work without migration params
    ),
    check_ruleset_name="azure_redis_latency",
    check_default_parameters={
        "serverside_upper": ("no_levels", None),
        "internode_upper": ("no_levels", None),
    },
)
