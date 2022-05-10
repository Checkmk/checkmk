#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping, Optional

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, render, Service, ServiceLabel
from cmk.base.plugins.agent_based.utils import gcp

from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


def parse_gcp_run(string_table: StringTable) -> gcp.Section:
    return gcp.parse_gcp(string_table, "service_name")


register.agent_section(name="gcp_service_cloud_run", parse_function=parse_gcp_run)

service_namer = gcp.service_name_factory("Cloud Run")


def discover(
    section_gcp_service_cloud_run: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> DiscoveryResult:
    if section_gcp_assets is None:
        return
    asset_type = "run.googleapis.com/Service"
    services = [a for a in section_gcp_assets if a.asset.asset_type == asset_type]
    for service in services:
        data = service.asset.resource.data
        item = data["metadata"]["name"]
        labels = [
            ServiceLabel("gcp/location", service.asset.resource.location),
            ServiceLabel("gcp/run/name", item),
            ServiceLabel("gcp/projectId", section_gcp_assets.project),
        ]
        yield Service(item=item, labels=labels)


def check_gcp_run_network(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_cloud_run: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> CheckResult:
    if section_gcp_service_cloud_run is None:
        return
    metrics = {
        "net_data_recv": gcp.MetricSpec(
            "run.googleapis.com/container/network/received_bytes_count",
            "Out",
            render.networkbandwidth,
        ),
        "net_data_sent": gcp.MetricSpec(
            "run.googleapis.com/container/network/sent_bytes_count", "In", render.networkbandwidth
        ),
    }
    timeseries = section_gcp_service_cloud_run.get(item, gcp.SectionItem(rows=[])).rows
    yield from gcp.generic_check(metrics, timeseries, params)


register.check_plugin(
    name="gcp_run_network",
    sections=["gcp_service_cloud_run", "gcp_assets"],
    service_name=service_namer("network"),
    check_ruleset_name="gcp_run_network",
    discovery_function=discover,
    check_function=check_gcp_run_network,
    check_default_parameters={"net_data_sent": None, "net_data_recv": None},
)


def check_gcp_run_memory(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_cloud_run: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> CheckResult:
    if section_gcp_service_cloud_run is None:
        return
    metrics = {
        # percent render expects numbers range 0 to 100 and not fractions.
        "memory_util": gcp.MetricSpec(
            "run.googleapis.com/container/memory/utilizations", "Memory", render.percent, scale=1e2
        ),
    }
    timeseries = section_gcp_service_cloud_run.get(item, gcp.SectionItem(rows=[])).rows
    yield from gcp.generic_check(metrics, timeseries, params)


register.check_plugin(
    name="gcp_run_memory",
    sections=["gcp_service_cloud_run", "gcp_assets"],
    service_name=service_namer("memory"),
    check_ruleset_name="gcp_run_memory",
    discovery_function=discover,
    check_function=check_gcp_run_memory,
    check_default_parameters={"memory_util": None},
)


def check_gcp_run_cpu(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_cloud_run: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> CheckResult:
    if section_gcp_service_cloud_run is None:
        return
    metrics = {
        "util": gcp.MetricSpec(
            "run.googleapis.com/container/cpu/utilizations", "CPU", render.percent, scale=1e2
        ),
    }
    timeseries = section_gcp_service_cloud_run.get(item, gcp.SectionItem(rows=[])).rows
    yield from gcp.generic_check(metrics, timeseries, params)


register.check_plugin(
    name="gcp_run_cpu",
    sections=["gcp_service_cloud_run", "gcp_assets"],
    service_name=service_namer("cpu"),
    check_ruleset_name="gcp_run_cpu",
    discovery_function=discover,
    check_function=check_gcp_run_cpu,
    check_default_parameters={"util": (80.0, 90.0)},
)


def check_gcp_run_requests(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_cloud_run: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> CheckResult:
    if section_gcp_service_cloud_run is None:
        return
    metrics = {
        "faas_total_instance_count": gcp.MetricSpec(
            "run.googleapis.com/container/instance_count", "Instances", str, dtype="int"
        ),
        "faas_execution_count": gcp.MetricSpec(
            "run.googleapis.com/container/request_count", "Requests", str, dtype="int"
        ),
        "gcp_billable_time": gcp.MetricSpec(
            "run.googleapis.com/container/billable_instance_time",
            "Billable Time",
            lambda x: f"{x:.2f} s/s",
        ),
        # timespan renderer expects seconds not milliseconds
        "faas_execution_times": gcp.MetricSpec(
            "run.googleapis.com/container/request_latencies",
            "Latencies",
            render.timespan,
            scale=1e3,
        ),
    }
    timeseries = section_gcp_service_cloud_run.get(item, gcp.SectionItem(rows=[])).rows
    yield from gcp.generic_check(metrics, timeseries, params)


register.check_plugin(
    name="gcp_run_requests",
    sections=["gcp_service_cloud_run", "gcp_assets"],
    service_name=service_namer("requests"),
    check_ruleset_name="gcp_run_requests",
    discovery_function=discover,
    check_function=check_gcp_run_requests,
    check_default_parameters={
        "faas_total_instance_count": None,
        "faas_execution_count": None,
        "gcp_billable_time": None,
        "faas_execution_times": None,
    },
)
