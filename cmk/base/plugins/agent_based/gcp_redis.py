#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs
from typing import Any, Mapping, Optional

from .agent_based_api.v1 import register, render, Service, ServiceLabel
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import gcp, redis


def parse(string_table: StringTable) -> gcp.Section:
    return gcp.parse_gcp(string_table, "instance_id")


register.agent_section(name="gcp_service_redis", parse_function=parse)

service_namer = gcp.service_name_factory("Redis")
ASSET_TYPE = "redis.googleapis.com/Instance"


def discover(
    section_gcp_service_redis: Optional[gcp.Section], section_gcp_assets: Optional[gcp.AssetSection]
) -> DiscoveryResult:
    if section_gcp_assets is None or not section_gcp_assets.config.is_enabled("redis"):
        return
    instances = section_gcp_assets[ASSET_TYPE]
    for item, instance in instances.items():
        data = instance.resource_data
        labels = []
        labels.append(ServiceLabel("gcp/location", data["locationId"]))
        labels.append(ServiceLabel("gcp/projectId", section_gcp_assets.project))
        labels.append(ServiceLabel("gcp/redis/version", data["redisVersion"]))
        # TODO: more for inventory
        labels.append(ServiceLabel("gcp/redis/host", data["host"]))
        labels.append(ServiceLabel("gcp/redis/port", str(int(data["port"]))))
        labels.append(ServiceLabel("gcp/redis/tier", data["tier"]))
        labels.append(ServiceLabel("gcp/redis/nr_nodes", str(len(data["nodes"]))))
        labels.append(ServiceLabel("gcp/redis/connectMode", data["connectMode"]))
        labels.append(ServiceLabel("gcp/redis/displayname", data["displayName"]))
        yield Service(item=item, labels=labels)


def check_cpu_util(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_redis: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> CheckResult:
    metrics = {
        "util": gcp.MetricSpec(
            "redis.googleapis.com/stats/cpu_utilization", "Utilization", render.percent, scale=1e2
        )
    }
    yield from gcp.check(
        metrics, item, params, section_gcp_service_redis, ASSET_TYPE, section_gcp_assets
    )


register.check_plugin(
    name="gcp_redis_cpu",
    sections=["gcp_service_redis", "gcp_assets"],
    service_name=service_namer("CPU"),
    check_ruleset_name="gcp_redis_cpu",
    discovery_function=discover,
    check_function=check_cpu_util,
    check_default_parameters={"util": (80.0, 90.0)},
)


def check_memory_util(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_redis: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> CheckResult:
    metrics = {
        "memory_util": gcp.MetricSpec(
            "redis.googleapis.com/stats/memory/usage_ratio",
            "Memory utilization",
            render.percent,
            scale=1e2,
        ),
        "system_memory_util": gcp.MetricSpec(
            "redis.googleapis.com/stats/memory/system_memory_usage_ratio",
            "System memory utilization",
            render.percent,
            scale=1e2,
        ),
    }
    yield from gcp.check(
        metrics, item, params, section_gcp_service_redis, ASSET_TYPE, section_gcp_assets
    )


register.check_plugin(
    name="gcp_redis_memory",
    sections=["gcp_service_redis", "gcp_assets"],
    service_name=service_namer("memory"),
    check_ruleset_name="gcp_redis_memory",
    discovery_function=discover,
    check_function=check_memory_util,
    check_default_parameters={"memory_util": (80.0, 90.0), "system_memory_util": (80.0, 90.0)},
)


def check_hitratio(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_redis: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> CheckResult:
    if section_gcp_service_redis is None:
        return
    if section_gcp_assets is None or item not in section_gcp_assets[ASSET_TYPE]:
        return
    metric = gcp.MetricSpec(
        "redis.googleapis.com/stats/cache_hit_ratio",
        "",
        str,
    )
    timeseries = section_gcp_service_redis.get(item, gcp.SectionItem(rows=[])).rows
    hitratio = gcp._get_value(timeseries, metric)
    yield from redis.check_cache_hitratio(hitratio, params)


register.check_plugin(
    name="gcp_redis_hitratio",
    sections=["gcp_service_redis", "gcp_assets"],
    service_name=service_namer("hitratio"),
    check_ruleset_name="redis_hitratio",
    discovery_function=discover,
    check_function=check_hitratio,
    check_default_parameters={"levels_upper_hitratio": None, "levels_lower_hitratio": None},
)


def discovery_summary(section: gcp.AssetSection) -> DiscoveryResult:
    yield from gcp.discovery_summary(section, "redis")


def check_summary(section: gcp.AssetSection) -> CheckResult:
    yield from gcp.check_summary(ASSET_TYPE, "Instance", section)


register.check_plugin(
    name="gcp_redis_summary",
    sections=["gcp_assets"],
    service_name=service_namer.summary_name(),
    discovery_function=discovery_summary,
    check_function=check_summary,
)


def check_connected_clients(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_redis: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> CheckResult:
    if section_gcp_service_redis is None:
        return
    if section_gcp_assets is None or item not in section_gcp_assets[ASSET_TYPE]:
        return
    metric = gcp.MetricSpec(
        "redis.googleapis.com/clients/connected",
        "",
        str,
    )
    timeseries = section_gcp_service_redis.get(item, gcp.SectionItem(rows=[])).rows
    connected_clients = gcp._get_value(timeseries, metric)
    yield from redis.check_clients_connected(connected_clients, params)


register.check_plugin(
    name="gcp_redis_clients_connected",
    sections=["gcp_service_redis", "gcp_assets"],
    service_name=service_namer("clients_connected"),
    check_ruleset_name="gcp_redis_clients_connected",
    discovery_function=discover,
    check_function=check_connected_clients,
    check_default_parameters={"clients_connected": None},
)
