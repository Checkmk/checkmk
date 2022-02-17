#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping

from cmk.base.plugins.agent_based.utils import gcp
from cmk.base.plugins.agent_based.utils.gcp import discover

from .agent_based_api.v1 import register, render
from .agent_based_api.v1.type_defs import CheckResult, StringTable


def parse_gcp_run(string_table: StringTable) -> gcp.Section:
    return gcp.parse_gcp(string_table, "service_name")


register.agent_section(name="gcp_service_cloud_run", parse_function=parse_gcp_run)


def check_gcp_run_network(
    item: str, params: Mapping[str, Any], section: gcp.Section
) -> CheckResult:
    metrics = {
        "net_data_recv": gcp.MetricSpec(
            "run.googleapis.com/container/network/received_bytes_count", render.filesize
        ),
        "net_data_sent": gcp.MetricSpec(
            "run.googleapis.com/container/network/sent_bytes_count", render.filesize
        ),
    }
    timeseries = section[item].rows
    yield from gcp.generic_check(metrics, timeseries, params)


register.check_plugin(
    name="gcp_run_network",
    sections=["gcp_service_cloud_run"],
    service_name="GCP Cloud Run network %s",
    check_ruleset_name="gcp_run_network",
    discovery_function=discover,
    check_function=check_gcp_run_network,
    check_default_parameters={},
)


def check_gcp_run_memory(item: str, params: Mapping[str, Any], section: gcp.Section) -> CheckResult:
    metrics = {
        # percent render expects numbers range 0 to 100 and not fractions.
        "memory_util": gcp.MetricSpec(
            "run.googleapis.com/container/memory/utilizations", render.percent, scale=1e2
        ),
    }
    timeseries = section[item].rows
    yield from gcp.generic_check(metrics, timeseries, params)


register.check_plugin(
    name="gcp_run_memory",
    sections=["gcp_service_cloud_run"],
    service_name="GCP Cloud Run memory %s",
    check_ruleset_name="gcp_run_memory",
    discovery_function=discover,
    check_function=check_gcp_run_memory,
    check_default_parameters={},
)


def check_gcp_run_cpu(item: str, params: Mapping[str, Any], section: gcp.Section) -> CheckResult:
    metrics = {
        "util": gcp.MetricSpec(
            "run.googleapis.com/container/cpu/utilizations", render.percent, scale=1e2
        ),
    }
    timeseries = section[item].rows
    yield from gcp.generic_check(metrics, timeseries, params)


register.check_plugin(
    name="gcp_run_cpu",
    sections=["gcp_service_cloud_run"],
    service_name="GCP Cloud Run cpu %s",
    check_ruleset_name="gcp_run_cpu",
    discovery_function=discover,
    check_function=check_gcp_run_cpu,
    check_default_parameters={},
)


def check_gcp_run_requests(
    item: str, params: Mapping[str, Any], section: gcp.Section
) -> CheckResult:
    metrics = {
        "faas_total_instance_count": gcp.MetricSpec(
            "run.googleapis.com/container/instance_count", str
        ),
        "faas_execution_count": gcp.MetricSpec("run.googleapis.com/container/request_count", str),
        "gcp_billable_time": gcp.MetricSpec(
            "run.googleapis.com/container/billable_instance_time", lambda x: f"{x:.2f} s/s"
        ),
        # timespan renderer expects seconds not milliseconds
        "faas_execution_times": gcp.MetricSpec(
            "run.googleapis.com/container/request_latencies", render.timespan, scale=1e3
        ),
    }
    timeseries = section[item].rows
    yield from gcp.generic_check(metrics, timeseries, params)


register.check_plugin(
    name="gcp_run_requests",
    sections=["gcp_service_cloud_run"],
    service_name="GCP Cloud Run requests %s",
    check_ruleset_name="gcp_run_requests",
    discovery_function=discover,
    check_function=check_gcp_run_requests,
    check_default_parameters={},
)
