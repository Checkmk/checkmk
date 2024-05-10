#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs
import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    render,
    Service,
    StringTable,
)
from cmk.plugins.gcp.lib import gcp
from cmk.plugins.lib import interfaces, uptime


def parse_gce_uptime(string_table: StringTable) -> uptime.Section | None:
    if not string_table:
        return None
    section = gcp.parse_piggyback(string_table)
    metric = gcp.MetricExtractionSpec("compute.googleapis.com/instance/uptime_total")
    uptime_sec = gcp.get_value(section, metric)
    return uptime.Section(uptime_sec, None)


agent_section_gcp_service_gce_uptime_total = AgentSection(
    name="gcp_service_gce_uptime_total",
    parsed_section_name="gcp_gce_uptime",
    parse_function=parse_gce_uptime,
)

check_plugin_gcp_gce_uptime = CheckPlugin(
    name="gcp_gce_uptime",
    service_name="GCP/GCE Uptime",
    discovery_function=uptime.discover,
    check_function=uptime.check,
    check_ruleset_name="uptime",
    check_default_parameters={},
)


def parse_default(string_table: StringTable) -> gcp.PiggyBackSection | None:
    if not string_table:
        return None
    return gcp.parse_piggyback(string_table)


agent_section_gcp_service_gce_cpu = AgentSection(
    name="gcp_service_gce_cpu",
    parsed_section_name="gcp_gce_cpu",
    parse_function=parse_default,
)


def discover_default(section: gcp.PiggyBackSection) -> DiscoveryResult:
    yield Service()


def check_cpu(params: Mapping[str, Any], section: gcp.PiggyBackSection) -> CheckResult:
    metrics = {
        "util": gcp.MetricSpec(
            gcp.MetricExtractionSpec(
                metric_type="compute.googleapis.com/instance/cpu/utilization", scale=1e2
            ),
            gcp.MetricDisplaySpec(label="Utilization", render_func=render.percent),
        ),
        "vcores": gcp.MetricSpec(
            gcp.MetricExtractionSpec(
                metric_type="compute.googleapis.com/instance/cpu/reserved_cores",
            ),
            gcp.MetricDisplaySpec(label="Reserved vCores", render_func=str),
        ),
    }
    yield from gcp.generic_check(metrics, section, params)


check_plugin_gcp_gce_cpu = CheckPlugin(
    name="gcp_gce_cpu",
    service_name="GCP/GCE CPU utilization",
    discovery_function=discover_default,
    check_function=check_cpu,
    check_ruleset_name="gcp_gce_cpu",
    check_default_parameters={"util": (80.0, 90.0), "vcores": None},
)


agent_section_gcp_service_gce_network = AgentSection(
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
            gcp.MetricExtractionSpec(
                "compute.googleapis.com/instance/network/received_bytes_count",
            ),
            gcp.MetricDisplaySpec(label="", render_func=render.timespan),
        ),
        "out": gcp.MetricSpec(
            gcp.MetricExtractionSpec(
                "compute.googleapis.com/instance/network/sent_bytes_count",
            ),
            gcp.MetricDisplaySpec(label="", render_func=render.timespan),
        ),
    }
    metrics = {k: gcp.get_value(section, desc.extraction) for k, desc in metric_descs.items()}
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


check_plugin_gcp_gce_network = CheckPlugin(
    name="gcp_gce_network",
    service_name="GCP/GCE Network IO %s",
    discovery_function=discover_network,
    check_ruleset_name="interfaces",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_network,
)

agent_section_gcp_service_gce_disk = AgentSection(
    name="gcp_service_gce_disk",
    parsed_section_name="gcp_gce_disk",
    parse_function=parse_default,
)


def check_disk_summary(params: Mapping[str, Any], section: gcp.PiggyBackSection) -> CheckResult:
    metrics = {
        "disk_read_throughput": gcp.MetricSpec(
            gcp.MetricExtractionSpec(
                "compute.googleapis.com/instance/disk/read_bytes_count",
            ),
            gcp.MetricDisplaySpec(label="Read", render_func=render.iobandwidth),
        ),
        "disk_write_throughput": gcp.MetricSpec(
            gcp.MetricExtractionSpec(
                "compute.googleapis.com/instance/disk/write_bytes_count",
            ),
            gcp.MetricDisplaySpec(label="Write", render_func=render.iobandwidth),
        ),
        "disk_read_ios": gcp.MetricSpec(
            gcp.MetricExtractionSpec(
                "compute.googleapis.com/instance/disk/read_ops_count",
            ),
            gcp.MetricDisplaySpec(label="Read operations", render_func=str),
        ),
        "disk_write_ios": gcp.MetricSpec(
            gcp.MetricExtractionSpec(
                "compute.googleapis.com/instance/disk/write_ops_count",
            ),
            gcp.MetricDisplaySpec(label="Write operations", render_func=str),
        ),
    }
    yield from gcp.generic_check(metrics, section, params)


check_plugin_gcp_gce_disk_summary = CheckPlugin(
    name="gcp_gce_disk_summary",
    sections=["gcp_gce_disk"],
    service_name="GCP/GCE Disk IO Summary",
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

check_plugin_gcp_gce_summary = CheckPlugin(
    name="gcp_gce_summary",
    sections=["gcp_assets"],
    service_name=service_namer.summary_name(),
    discovery_function=discovery_summary,
    check_function=check_summary,
)
