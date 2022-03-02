#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping

from cmk.base.plugins.agent_based.agent_based_api.v1 import render
from cmk.base.plugins.agent_based.utils import gcp
from cmk.base.plugins.agent_based.utils.gcp import discover

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import CheckResult, StringTable


def parse_gcp_function(string_table: StringTable) -> gcp.Section:
    return gcp.parse_gcp(string_table, "function_name")


register.agent_section(name="gcp_service_cloud_functions", parse_function=parse_gcp_function)


def check_gcp_function_instances(
    item: str, params: Mapping[str, Any], section: gcp.Section
) -> CheckResult:
    metrics = {
        "faas_total_instance_count": gcp.MetricSpec(
            "cloudfunctions.googleapis.com/function/instance_count", str
        ),
        "faas_active_instance_count": gcp.MetricSpec(
            "cloudfunctions.googleapis.com/function/active_instances", str
        ),
    }
    timeseries = section[item].rows
    yield from gcp.generic_check(metrics, timeseries, params)


register.check_plugin(
    name="gcp_function_instances",
    sections=["gcp_service_cloud_functions"],
    service_name="GCP Cloud Function instances %s",
    check_ruleset_name="gcp_function_instances",
    discovery_function=discover,
    check_function=check_gcp_function_instances,
    check_default_parameters={},
)


def check_gcp_function_execution(
    item: str, params: Mapping[str, Any], section: gcp.Section
) -> CheckResult:
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
    timeseries = section[item].rows
    yield from gcp.generic_check(metrics, timeseries, params)


register.check_plugin(
    name="gcp_function_execution",
    sections=["gcp_service_cloud_functions"],
    service_name="GCP Cloud Function execution %s",
    check_ruleset_name="gcp_function_execution",
    discovery_function=discover,
    check_function=check_gcp_function_execution,
    check_default_parameters={},
)


def check_gcp_function_egress(
    item: str, params: Mapping[str, Any], section: gcp.Section
) -> CheckResult:
    metrics = {
        "net_data_sent": gcp.MetricSpec(
            "cloudfunctions.googleapis.com/function/network_egress", render.bytes
        ),
    }
    timeseries = section[item].rows
    yield from gcp.generic_check(metrics, timeseries, params)


register.check_plugin(
    name="gcp_function_egress",
    sections=["gcp_service_cloud_functions"],
    service_name="GCP Cloud Function egress %s",
    check_ruleset_name="gcp_function_egress",
    discovery_function=discover,
    check_function=check_gcp_function_egress,
    check_default_parameters={},
)
