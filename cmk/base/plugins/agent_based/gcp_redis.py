#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping, Optional

from .agent_based_api.v1 import register, render, Service, ServiceLabel
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import gcp


def parse(string_table: StringTable) -> gcp.Section:
    return gcp.parse_gcp(string_table, "instance_id")


register.agent_section(name="gcp_service_redis", parse_function=parse)


def discover(
    section_gcp_service_redis: Optional[gcp.Section], section_gcp_assets: Optional[gcp.AssetSection]
) -> DiscoveryResult:
    if section_gcp_assets is None:
        return
    asset_type = "redis.googleapis.com/Instance"
    instances = [a for a in section_gcp_assets if a.asset.asset_type == asset_type]
    for instance in instances:
        data = instance.asset.resource.data
        # so this is long string because display name and UID are not the same.
        item = data["name"]
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
    if section_gcp_service_redis is None:
        return
    metrics = {
        "util": gcp.MetricSpec(
            "redis.googleapis.com/stats/cpu_utilization", "Utilization", render.percent, scale=1e2
        )
    }
    timeseries = section_gcp_service_redis.get(item, gcp.SectionItem(rows=[])).rows
    yield from gcp.generic_check(metrics, timeseries, params)


register.check_plugin(
    name="gcp_redis_cpu",
    sections=["gcp_service_redis", "gcp_assets"],
    service_name="GCP Redis CPU: %s",
    check_ruleset_name="gcp_redis_cpu",
    discovery_function=discover,
    check_function=check_cpu_util,
    check_default_parameters={"util": None},
)


def check_memory_util(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_redis: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> CheckResult:
    if section_gcp_service_redis is None:
        return
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
    timeseries = section_gcp_service_redis.get(item, gcp.SectionItem(rows=[])).rows
    yield from gcp.generic_check(metrics, timeseries, params)


register.check_plugin(
    name="gcp_redis_memory",
    sections=["gcp_service_redis", "gcp_assets"],
    service_name="GCP Redis Memory: %s",
    check_ruleset_name="gcp_redis_memory",
    discovery_function=discover,
    check_function=check_memory_util,
    check_default_parameters={"memory_util": None, "system_memory_util": None},
)
