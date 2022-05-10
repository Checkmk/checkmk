#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping, Optional

from .agent_based_api.v1 import register, render, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import gcp, uptime


def parse_gce_uptime(string_table: StringTable) -> Optional[uptime.Section]:
    if not string_table:
        return None
    section = gcp.parse_piggyback(string_table)
    metric = gcp.MetricSpec(
        "compute.googleapis.com/instance/uptime_total",
        "uptime",
        render.timespan,
        dtype=gcp.MetricSpec.DType.INT,
    )
    uptime_sec = gcp._get_value(section, metric)
    return uptime.Section(uptime_sec, None)


register.agent_section(
    name="gcp_service_gce_uptime_total",
    parsed_section_name="uptime",
    parse_function=parse_gce_uptime,
)


def parse_cpu(string_table: StringTable) -> Optional[gcp.PiggyBackSection]:
    if not string_table:
        return None
    return gcp.parse_piggyback(string_table)


register.agent_section(
    name="gcp_service_gce_cpu",
    parsed_section_name="gcp_gce_cpu",
    parse_function=parse_cpu,
)


def discover_cpu(section: gcp.PiggyBackSection) -> DiscoveryResult:
    yield Service()


def check_cpu(params: Mapping[str, Any], section: gcp.PiggyBackSection) -> CheckResult:
    metrics = {
        "util": gcp.MetricSpec(
            "compute.googleapis.com/instance/cpu/utilization",
            "Utilization",
            render.percent,
            scale=1e2,
        ),
        "vcores": gcp.MetricSpec(
            "compute.googleapis.com/instance/cpu/reserved_cores",
            "Reserved vCores",
            str,
        ),
    }
    yield from gcp.generic_check(metrics, section, params)


register.check_plugin(
    name="gcp_gce_cpu",
    service_name="CPU",
    discovery_function=discover_cpu,
    check_function=check_cpu,
    check_ruleset_name="gcp_gce_cpu",
    check_default_parameters={"util": (80.0, 90.0), "vcores": None},
)
