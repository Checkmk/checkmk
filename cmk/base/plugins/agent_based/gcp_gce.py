#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs
import time
from collections.abc import Mapping
from typing import Any

from .agent_based_api.v1 import get_value_store, register, render, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import gcp, interfaces, uptime


def parse_gce_uptime(string_table: StringTable) -> uptime.Section | None:
    if not string_table:
        return None
    section = gcp.parse_piggyback(string_table)
    metric = gcp.MetricSpec(
        "compute.googleapis.com/instance/uptime_total",
        "uptime",
        render.timespan,
    )
    uptime_sec = gcp.get_value(section, metric)
    return uptime.Section(uptime_sec, None)


register.agent_section(
    name="gcp_service_gce_uptime_total",
    parsed_section_name="uptime",
    parse_function=parse_gce_uptime,
)


def parse_default(string_table: StringTable) -> gcp.PiggyBackSection | None:
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
    metrics = {k: gcp.get_value(section, desc) for k, desc in metric_descs.items()}
    interface = interfaces.InterfaceWithRatesAndAverages.from_interface_with_counters_or_rates(
        interfaces.InterfaceWithRates(
            attributes=interfaces.Attributes(
                index="0",
                descr=item,
                alias=item,
                type="1",
                oper_status="1",
            ),
            rates=interfaces.Rates(
                in_octets=metrics["in"],
                out_octets=metrics["out"],
            ),
            get_rate_errors=[],
        ),
        timestamp=time.time(),
        value_store=get_value_store(),
        params=params,
    )
    yield from interfaces.check_single_interface(item, params, interface)


register.check_plugin(
    name="gcp_gce_network",
    service_name="Network IO %s",
    discovery_function=discover_network,
    check_ruleset_name="if",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
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


ASSET_TYPE = gcp.AssetType("compute.googleapis.com/Instance")


def discovery_summary(section: gcp.AssetSection) -> DiscoveryResult:
    yield from gcp.discovery_summary(section, "gce")


def check_summary(section: gcp.AssetSection) -> CheckResult:
    yield from gcp.check_summary(ASSET_TYPE, "VM", section)


service_namer = gcp.service_name_factory("GCE")

register.check_plugin(
    name="gcp_gce_summary",
    sections=["gcp_assets"],
    service_name=service_namer.summary_name(),
    discovery_function=discovery_summary,
    check_function=check_summary,
)
