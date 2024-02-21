#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
    StringTable,
)
from cmk.plugins.gcp.lib import gcp


def parse(string_table: StringTable) -> gcp.Section:
    return gcp.parse_gcp(string_table, gcp.ResourceKey("url_map_name"))


agent_section_gcp_service_http_lb = AgentSection(name="gcp_service_http_lb", parse_function=parse)


service_namer = gcp.service_name_factory("HTTP(S) load balancer")
SECTIONS = ["gcp_service_http_lb", "gcp_assets"]
ASSET_TYPE = gcp.AssetType("compute.googleapis.com/UrlMap")


def discover(
    section_gcp_service_http_lb: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> DiscoveryResult:
    assets = gcp.validate_asset_section(section_gcp_assets, "http_lb")
    for item, _ in assets[ASSET_TYPE].items():
        yield Service(item=item, labels=[])


def check_requests(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_http_lb: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> CheckResult:
    metrics = {
        "requests": gcp.MetricSpec(
            gcp.MetricExtractionSpec(
                metric_type="loadbalancing.googleapis.com/https/request_count"
            ),
            gcp.MetricDisplaySpec(label="Requests", render_func=str),
        ),
    }
    yield from gcp.check(
        metrics, item, params, section_gcp_service_http_lb, ASSET_TYPE, section_gcp_assets
    )


check_plugin_gcp_http_lb_requests = CheckPlugin(
    name="gcp_http_lb_requests",
    sections=SECTIONS,
    service_name=service_namer("requests"),
    check_ruleset_name="gcp_http_lb_requests",
    discovery_function=discover,
    check_function=check_requests,
    check_default_parameters={"requests": None},
)


def check_latencies(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_http_lb: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> CheckResult:
    metrics = gcp.get_percentile_metric_specs(
        "loadbalancing.googleapis.com/https/total_latencies",
        "latencies",
        "Latency",
        render.timespan,
        scale=1e-3,
    )
    yield from gcp.check(
        metrics, item, params, section_gcp_service_http_lb, ASSET_TYPE, section_gcp_assets
    )


check_plugin_gcp_http_lb_latencies = CheckPlugin(
    name="gcp_http_lb_latencies",
    sections=SECTIONS,
    service_name=service_namer("latencies"),
    check_ruleset_name="gcp_http_lb_latencies",
    discovery_function=discover,
    check_function=check_latencies,
    check_default_parameters={"latencies": (99, None)},
)


def discovery_summary(section: gcp.AssetSection) -> DiscoveryResult:
    yield from gcp.discovery_summary(section, "HTTP_LB")


def check_summary(section: gcp.AssetSection) -> CheckResult:
    yield from gcp.check_summary(ASSET_TYPE, "load balancer", section)


check_plugin_gcp_http_lb_summary = CheckPlugin(
    name="gcp_http_lb_summary",
    sections=["gcp_assets"],
    service_name=service_namer.summary_name(),
    discovery_function=discovery_summary,
    check_function=check_summary,
)
