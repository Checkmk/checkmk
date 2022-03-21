#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping, Optional

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, render, Service, ServiceLabel
from cmk.base.plugins.agent_based.utils import gcp

from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


def parse_gcp_function(string_table: StringTable) -> gcp.Section:
    return gcp.parse_gcp(string_table, "function_name")


register.agent_section(name="gcp_service_cloud_functions", parse_function=parse_gcp_function)


def discover(
    section_gcp_service_cloud_functions: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> DiscoveryResult:
    if section_gcp_assets is None:
        return
    asset_type = "cloudfunctions.googleapis.com/CloudFunction"
    functions = [a for a in section_gcp_assets if a.asset.asset_type == asset_type]
    for function in functions:
        data = function.asset.resource.data
        item = data["name"].split("/")[-1]
        labels = [
            ServiceLabel("gcp/location", function.asset.resource.location),
            ServiceLabel("gcp/function/name", item),
            ServiceLabel("gcp/projectId", section_gcp_assets.project),
        ]
        yield Service(item=item, labels=labels)


def check_gcp_function_instances(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_cloud_functions: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> CheckResult:
    if section_gcp_service_cloud_functions is None:
        return
    section = section_gcp_service_cloud_functions
    metrics = {
        "faas_total_instance_count": gcp.MetricSpec(
            "cloudfunctions.googleapis.com/function/instance_count", str
        ),
        "faas_active_instance_count": gcp.MetricSpec(
            "cloudfunctions.googleapis.com/function/active_instances", str
        ),
    }
    timeseries = section.get(item, gcp.SectionItem(rows=[])).rows
    yield from gcp.generic_check(metrics, timeseries, params)


register.check_plugin(
    name="gcp_function_instances",
    sections=["gcp_service_cloud_functions", "gcp_assets"],
    service_name="GCP Cloud Function instances %s",
    check_ruleset_name="gcp_function_instances",
    discovery_function=discover,
    check_function=check_gcp_function_instances,
    check_default_parameters={},
)


def check_gcp_function_execution(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_cloud_functions: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> CheckResult:
    if section_gcp_service_cloud_functions is None:
        return
    section = section_gcp_service_cloud_functions
    metrics = {
        # TODO: this is the total. Separate by state
        "faas_execution_count": gcp.MetricSpec(
            "cloudfunctions.googleapis.com/function/execution_count", str
        ),
        "aws_lambda_memory_size_absolute": gcp.MetricSpec(
            "cloudfunctions.googleapis.com/function/user_memory_bytes", render.bytes
        ),
        # execution times are given in nanoseconds. timespan expects seconds.
        "faas_execution_times": gcp.MetricSpec(
            "cloudfunctions.googleapis.com/function/execution_times",
            render.timespan,
            scale=1e-9,
        ),
    }
    timeseries = section.get(item, gcp.SectionItem(rows=[])).rows
    yield from gcp.generic_check(metrics, timeseries, params)


register.check_plugin(
    name="gcp_function_execution",
    sections=["gcp_service_cloud_functions", "gcp_assets"],
    service_name="GCP Cloud Function execution %s",
    check_ruleset_name="gcp_function_execution",
    discovery_function=discover,
    check_function=check_gcp_function_execution,
    check_default_parameters={},
)


def check_gcp_function_network(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_cloud_functions: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> CheckResult:
    if section_gcp_service_cloud_functions is None:
        return
    section = section_gcp_service_cloud_functions
    metrics = {
        "net_data_sent": gcp.MetricSpec(
            "cloudfunctions.googleapis.com/function/network_egress", render.networkbandwidth
        ),
    }
    timeseries = section.get(item, gcp.SectionItem(rows=[])).rows
    yield from gcp.generic_check(metrics, timeseries, params)


register.check_plugin(
    name="gcp_function_network",
    sections=["gcp_service_cloud_functions", "gcp_assets"],
    service_name="GCP Cloud Function network %s",
    check_ruleset_name="gcp_function_network",
    discovery_function=discover,
    check_function=check_gcp_function_network,
    check_default_parameters={},
)
