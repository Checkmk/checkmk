#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping, Optional

from .agent_based_api.v1 import register, render, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import gcp, uptime
from .utils.interfaces import CHECK_DEFAULT_PARAMETERS, check_single_interface, Interface


def parse_gce_uptime(string_table: StringTable) -> Optional[uptime.Section]:
    if not string_table:
        return None
    section = gcp.parse_piggyback(string_table)
    metric = gcp.MetricSpec(
        "compute.googleapis.com/instance/uptime_total",
        "uptime",
        render.timespan,
    )
    uptime_sec = gcp._get_value(section, metric)
    return uptime.Section(uptime_sec, None)


register.agent_section(
    name="gcp_service_gce_uptime_total",
    parsed_section_name="uptime",
    parse_function=parse_gce_uptime,
)


def parse_default(string_table: StringTable) -> Optional[gcp.PiggyBackSection]:
    if not string_table:
        return None
    return gcp.parse_piggyback(string_table)


register.agent_section(
    name="gcp_service_gce_cpu",
    parsed_section_name="gcp_gce_cpu",
    parse_function=parse_default,
)


def discover_default(section: gcp.PiggyBackSection) -> DiscoveryResult:
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
    discovery_function=discover_default,
    check_function=check_cpu,
    check_ruleset_name="gcp_gce_cpu",
    check_default_parameters={"util": (80.0, 90.0), "vcores": None},
)


register.agent_section(
    name="gcp_service_gce_network",
    parsed_section_name="gcp_gce_network",
    parse_function=parse_default,
)


def discover_network(section: gcp.PiggyBackSection) -> DiscoveryResult:
    yield Service(item="nic0")


def check_network(
    item: str, params: Mapping[str, Any], section: gcp.PiggyBackSection
) -> CheckResult:
    metric_descs = {
        "in": gcp.MetricSpec(
            "compute.googleapis.com/instance/network/received_bytes_count",
            "",
            render.timespan,
        ),
        "out": gcp.MetricSpec(
            "compute.googleapis.com/instance/network/sent_bytes_count",
            "",
            render.timespan,
        ),
    }
    metrics = {k: gcp._get_value(section, desc) for k, desc in metric_descs.items()}
    interface = Interface(
        index="0",
        descr=item,
        alias=item,
        type="1",
        oper_status="1",
        in_octets=metrics["in"],
        out_octets=metrics["out"],
    )
    yield from check_single_interface(item, params, interface, input_is_rate=True)


register.check_plugin(
    name="gcp_gce_network",
    service_name="Network IO %s",
    discovery_function=discover_network,
    check_ruleset_name="if",
    check_default_parameters=CHECK_DEFAULT_PARAMETERS,
    check_function=check_network,
)

register.agent_section(
    name="gcp_service_gce_disk",
    parsed_section_name="gcp_gce_disk",
    parse_function=parse_default,
)


def check_disk_summary(params: Mapping[str, Any], section: gcp.PiggyBackSection) -> CheckResult:
    metrics = {
        "disk_read_throughput": gcp.MetricSpec(
            "compute.googleapis.com/instance/disk/read_bytes_count",
            "Read",
            render.iobandwidth,
        ),
        "disk_write_throughput": gcp.MetricSpec(
            "compute.googleapis.com/instance/disk/write_bytes_count",
            "Write",
            render.iobandwidth,
        ),
        "disk_read_ios": gcp.MetricSpec(
            "compute.googleapis.com/instance/disk/read_ops_count",
            "Read operations",
            str,
        ),
        "disk_write_ios": gcp.MetricSpec(
            "compute.googleapis.com/instance/disk/write_ops_count",
            "Write operations",
            str,
        ),
    }
    yield from gcp.generic_check(metrics, section, params)


register.check_plugin(
    name="gcp_gce_disk_summary",
    sections=["gcp_gce_disk"],
    service_name="Instance disk IO",
    discovery_function=discover_default,
    check_ruleset_name="gcp_gce_disk",
    check_default_parameters={
        "disk_read_throughput": None,
        "disk_write_throughput": None,
        "disk_read_ios": None,
        "disk_write_ios": None,
    },
    check_function=check_disk_summary,
)
