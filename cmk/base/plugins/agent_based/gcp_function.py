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

service_namer = gcp.service_name_factory("Function")
ASSET_TYPE = "cloudfunctions.googleapis.com/CloudFunction"


def discover(
    section_gcp_service_cloud_functions: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> DiscoveryResult:
    if section_gcp_assets is None or not section_gcp_assets.config.is_enabled("cloud_functions"):
        return
    functions = section_gcp_assets[ASSET_TYPE]
    for item, function in functions.items():
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
    metrics = {
        "faas_total_instance_count": gcp.MetricSpec(
            "cloudfunctions.googleapis.com/function/instance_count", "Instances", str
        ),
        "faas_active_instance_count": gcp.MetricSpec(
            "cloudfunctions.googleapis.com/function/active_instances", "Active instances", str
        ),
    }
    yield from gcp.check(
        metrics, item, params, section_gcp_service_cloud_functions, ASSET_TYPE, section_gcp_assets
    )


register.check_plugin(
    name="gcp_function_instances",
    sections=["gcp_service_cloud_functions", "gcp_assets"],
    service_name=service_namer("instances"),
    check_ruleset_name="gcp_function_instances",
    discovery_function=discover,
    check_function=check_gcp_function_instances,
    check_default_parameters={
        "faas_total_instance_count": None,
        "faas_active_instance_count": None,
    },
)


def check_gcp_function_execution(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_cloud_functions: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> CheckResult:
    metrics = {
        # TODO: this is the total. Separate by state
        "faas_execution_count": gcp.MetricSpec(
            "cloudfunctions.googleapis.com/function/execution_count", "Executions count", str
        ),
        "aws_lambda_memory_size_absolute": gcp.MetricSpec(
            "cloudfunctions.googleapis.com/function/user_memory_bytes", "Memory", render.bytes
        ),
        # execution times are given in nanoseconds. timespan expects seconds.
        "faas_execution_times": gcp.MetricSpec(
            "cloudfunctions.googleapis.com/function/execution_times",
            "Execution times",
            render.timespan,
            scale=1e-9,
        ),
    }
    yield from gcp.check(
        metrics, item, params, section_gcp_service_cloud_functions, ASSET_TYPE, section_gcp_assets
    )


register.check_plugin(
    name="gcp_function_execution",
    sections=["gcp_service_cloud_functions", "gcp_assets"],
    service_name=service_namer("execution"),
    check_ruleset_name="gcp_function_execution",
    discovery_function=discover,
    check_function=check_gcp_function_execution,
    check_default_parameters={
        "faas_execution_count": None,
        "faas_execution_times": None,
        "aws_lambda_memory_size_absolute": None,
    },
)


def check_gcp_function_network(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_cloud_functions: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> CheckResult:
    metrics = {
        "net_data_sent": gcp.MetricSpec(
            "cloudfunctions.googleapis.com/function/network_egress", "Out", render.networkbandwidth
        ),
    }
    yield from gcp.check(
        metrics, item, params, section_gcp_service_cloud_functions, ASSET_TYPE, section_gcp_assets
    )


register.check_plugin(
    name="gcp_function_network",
    sections=["gcp_service_cloud_functions", "gcp_assets"],
    service_name=service_namer("network"),
    check_ruleset_name="gcp_function_network",
    discovery_function=discover,
    check_function=check_gcp_function_network,
    check_default_parameters={"net_data_sent": None},
)
