#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    IgnoreResultsError,
    InventoryPlugin,
    render,
    Result,
    State,
)
from cmk.agent_based.v2 import check_levels as check_levels_v2
from cmk.plugins.azure_v2.agent_based.lib import (
    check_resource_metrics,
    create_check_metrics_function_single,
    create_discover_by_metrics_function_single,
    inventory_common_azure,
    MetricData,
    parse_resources,
    Section,
)

agent_section_azure_redis = AgentSection(name="azure_v2_redis", parse_function=parse_resources)

inventory_plugin_azure_redis = InventoryPlugin(
    name="azure_v2_redis",
    inventory_function=inventory_common_azure,
)

check_plugin_azure_redis_connections = CheckPlugin(
    name="azure_v2_redis_connections",
    sections=["azure_v2_redis"],
    service_name="Azure/Redis Connections",
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
        check_levels=check_levels_v2,
    ),
    check_ruleset_name="azure_v2_redis_connections",
    check_default_parameters={
        "connected_clients": ("fixed", (200, 250)),
        "created_connections": ("no_levels", None),
    },
)


check_plugin_azure_redis_cpu_utilization = CheckPlugin(
    name="azure_v2_redis_cpu_utilization",
    sections=["azure_v2_redis"],
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
                upper_levels_param="cpu_utilization",
                average_mins_param="average_mins",
                sustained_threshold_param=(
                    lambda params: params.get("for_time", {}).get("threshold_for_time")
                ),
                sustained_levels_time_param=(
                    lambda params: params.get("for_time", {}).get("limit_secs_for_time")
                ),
                sustained_label="CPU utilization high for",
            ),
        ],
        check_levels=check_levels_v2,
    ),
    check_ruleset_name="azure_v2_redis_cpu_utilization",
    check_default_parameters={
        "cpu_utilization": ("fixed", (70.0, 80.0)),
    },
)


check_plugin_azure_redis_cache_effectiveness = CheckPlugin(
    name="azure_v2_redis_cache_effectiveness",
    sections=["azure_v2_redis"],
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
        check_levels=check_levels_v2,
    ),
    check_ruleset_name="azure_v2_redis_cache_effectiveness",
    check_default_parameters={
        "cache_hit_ratio": ("fixed", (85.0, 80.0)),
    },
)


check_plugin_azure_redis_memory = CheckPlugin(
    name="azure_v2_redis_memory",
    sections=["azure_v2_redis"],
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
        check_levels=check_levels_v2,
    ),
    check_ruleset_name="azure_v2_redis_memory",
    check_default_parameters={
        "memory_util": ("fixed", (70.0, 80.0)),
        "evicted_keys": ("no_levels", None),
    },
)

check_plugin_azure_redis_latency = CheckPlugin(
    name="azure_v2_redis_latency",
    sections=["azure_v2_redis"],
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
        check_levels=check_levels_v2,
    ),
    check_ruleset_name="azure_v2_redis_latency",
    check_default_parameters={
        "serverside_upper": ("no_levels", None),
        "internode_upper": ("fixed", (0.5, 1.0)),
    },
)


def check_azure_redis_replication(params: Mapping[str, Any], section: Section) -> CheckResult:
    """
    Check function for Azure Redis replication.

    This needs to be a special snowflake, because we effectively get a boolean
    value back as one of the metrics ("GeoReplicationHealthy" will be 1 if
    healthy, 0 otherwise). So we need to process that and then take into account
    what status the param asks for when it's reported unhealthy (0).

    For "GeoReplicationConnectivityLag" we can use the normal
    check_resource_metrics, since it's just in seconds.
    """
    if len(section) != 1:
        raise IgnoreResultsError("Only one resource expected")

    resource = list(section.values())[0]
    health_metric = resource.metrics.get("minimum_GeoReplicationHealthy")
    if health_metric is not None:
        is_healthy = health_metric.value == 1
        if is_healthy:
            yield Result(state=State.OK, summary="Healthy")
        else:
            yield Result(state=State(params["replication_unhealthy_status"]), summary="Unhealthy")

    yield from check_resource_metrics(
        resource,
        params,
        [
            MetricData(
                "average_GeoReplicationConnectivityLag",
                "azure_redis_replication_connectivity_lag",
                "Connectivity lag",
                render.timespan,
                upper_levels_param="replication_connectivity_lag_upper",
            ),
        ],
        check_levels=check_levels_v2,
    )


check_plugin_azure_redis_replication = CheckPlugin(
    name="azure_v2_redis_replication",
    sections=["azure_v2_redis"],
    service_name="Azure/Redis Replication",
    discovery_function=create_discover_by_metrics_function_single(
        "minimum_GeoReplicationHealthy",
        "average_GeoReplicationConnectivityLag",
    ),
    check_function=check_azure_redis_replication,
    check_ruleset_name="azure_v2_redis_replication",
    check_default_parameters={
        "replication_unhealthy_status": int(State.CRIT),
        "replication_connectivity_lag_upper": ("no_levels", None),
    },
)

check_plugin_azure_redis_throughput = CheckPlugin(
    name="azure_v2_redis_throughput",
    sections=["azure_v2_redis"],
    service_name="Azure/Redis Throughput",
    discovery_function=create_discover_by_metrics_function_single(
        "maximum_allcacheRead",
        "maximum_allcacheWrite",
    ),
    check_function=create_check_metrics_function_single(
        [
            MetricData(
                "maximum_allcacheRead",
                "azure_redis_throughput_cache_read",
                "Read",
                render.iobandwidth,
                upper_levels_param="cache_read_upper",
            ),
            MetricData(
                "maximum_allcacheWrite",
                "azure_redis_throughput_cache_write",
                "Write",
                render.iobandwidth,
                upper_levels_param="cache_write_upper",
            ),
        ],
        check_levels=check_levels_v2,
    ),
    check_ruleset_name="azure_v2_redis_throughput",
    check_default_parameters={
        "cache_read_upper": ("no_levels", None),
        "cache_write_upper": ("no_levels", None),
    },
)

check_plugin_azure_redis_server_load = CheckPlugin(
    name="azure_v2_redis_server_load",
    sections=["azure_v2_redis"],
    service_name="Azure/Redis Server load",
    discovery_function=create_discover_by_metrics_function_single(
        "maximum_serverLoad",
    ),
    check_function=create_check_metrics_function_single(
        [
            MetricData(
                "maximum_serverLoad",
                "azure_redis_server_load",
                "Server load",
                render.percent,
                upper_levels_param="levels",
                average_mins_param="average_mins",
                sustained_threshold_param=(
                    lambda params: params.get("for_time", {}).get("threshold_for_time")
                ),
                sustained_levels_time_param=(
                    lambda params: params.get("for_time", {}).get("limit_secs_for_time")
                ),
                sustained_label="Server under high load for",
            ),
        ],
        check_levels=check_levels_v2,
    ),
    check_ruleset_name="azure_v2_redis_server_load",
    check_default_parameters={
        "levels": ("fixed", (85.0, 90.0)),
    },
)
