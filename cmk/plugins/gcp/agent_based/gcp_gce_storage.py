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
    ServiceLabel,
    StringTable,
)
from cmk.plugins.gcp.lib import gcp


def parse(string_table: StringTable) -> gcp.Section:
    return gcp.parse_gcp(string_table, gcp.MetricKey("device_name"))


agent_section_gcp_service_gce_storage = AgentSection(
    name="gcp_service_gce_storage", parse_function=parse
)


service_namer = gcp.service_name_factory("GCE Disk")
SECTIONS = ["gcp_service_gce_storage", "gcp_assets"]
ASSET_TYPE = gcp.AssetType("compute.googleapis.com/Disk")


def discover(
    section_gcp_service_gce_storage: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> DiscoveryResult:
    assets = gcp.validate_asset_section(section_gcp_assets, "gce_storage")
    for item, bucket in assets[ASSET_TYPE].items():
        data = bucket.resource_data
        labels = [ServiceLabel(f"cmk/gcp/labels/{k}", v) for k, v in data.get("labels", {}).items()]
        labels.append(ServiceLabel("cmk/gcp/location", bucket.location))
        yield Service(item=item, labels=labels)


def check_storage(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_gce_storage: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> CheckResult:
    metrics = {
        "disk_read_throughput": gcp.MetricSpec(
            gcp.MetricExtractionSpec(
                metric_type="compute.googleapis.com/instance/disk/read_bytes_count"
            ),
            gcp.MetricDisplaySpec(label="Read", render_func=render.iobandwidth),
        ),
        "disk_write_throughput": gcp.MetricSpec(
            gcp.MetricExtractionSpec(
                metric_type="compute.googleapis.com/instance/disk/write_bytes_count"
            ),
            gcp.MetricDisplaySpec(label="Write", render_func=render.iobandwidth),
        ),
        "disk_read_ios": gcp.MetricSpec(
            gcp.MetricExtractionSpec(
                metric_type="compute.googleapis.com/instance/disk/read_ops_count"
            ),
            gcp.MetricDisplaySpec(label="Read operations", render_func=str),
        ),
        "disk_write_ios": gcp.MetricSpec(
            gcp.MetricExtractionSpec(
                metric_type="compute.googleapis.com/instance/disk/write_ops_count"
            ),
            gcp.MetricDisplaySpec(label="Write operations", render_func=str),
        ),
    }
    yield from gcp.check(
        metrics, item, params, section_gcp_service_gce_storage, ASSET_TYPE, section_gcp_assets
    )


check_plugin_gcp_gce_storage = CheckPlugin(
    name="gcp_gce_storage",
    sections=SECTIONS,
    service_name=service_namer("disk"),
    check_ruleset_name="gcp_gce_storage",
    discovery_function=discover,
    check_function=check_storage,
    check_default_parameters={
        "disk_read_throughput": None,
        "disk_write_throughput": None,
        "disk_write_ios": None,
        "disk_read_ios": None,
    },
)


def discovery_summary(section: gcp.AssetSection) -> DiscoveryResult:
    yield from gcp.discovery_summary(section, "gcs")


def check_summary(section: gcp.AssetSection) -> CheckResult:
    yield from gcp.check_summary(ASSET_TYPE, "Disk", section)


check_plugin_gcp_gce_storage_summary = CheckPlugin(
    name="gcp_gce_storage_summary",
    sections=["gcp_assets"],
    service_name=service_namer.summary_name(),
    discovery_function=discovery_summary,
    check_function=check_summary,
)
