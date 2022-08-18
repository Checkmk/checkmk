#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs
from typing import Any, Mapping, Optional

from .agent_based_api.v1 import register, render, Service, ServiceLabel
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import gcp


def parse(string_table: StringTable) -> gcp.Section:
    return gcp.parse_gcp(string_table, gcp.MetricKey("device_name"))


register.agent_section(name="gcp_service_gce_storage", parse_function=parse)


service_namer = gcp.service_name_factory("GCE Disk")
SECTIONS = ["gcp_service_gce_storage", "gcp_assets"]
ASSET_TYPE = gcp.AssetType("compute.googleapis.com/Disk")


def discover(
    section_gcp_service_gce_storage: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> DiscoveryResult:
    if (
        section_gcp_assets is None
        or not section_gcp_assets.config.is_enabled("gce_storage")
        or not ASSET_TYPE in section_gcp_assets
    ):
        return
    for item, bucket in section_gcp_assets[ASSET_TYPE].items():
        data = bucket.resource_data
        labels = [ServiceLabel(f"gcp/labels/{k}", v) for k, v in data.get("labels", {}).items()]
        labels.append(ServiceLabel("gcp/location", bucket.location))
        labels.append(ServiceLabel("gcp/projectId", section_gcp_assets.project))
        yield Service(item=item, labels=labels)


def check_storage(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_gce_storage: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> CheckResult:
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
    yield from gcp.check(
        metrics, item, params, section_gcp_service_gce_storage, ASSET_TYPE, section_gcp_assets
    )


register.check_plugin(
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


register.check_plugin(
    name="gcp_gce_storage_summary",
    sections=["gcp_assets"],
    service_name=service_namer.summary_name(),
    discovery_function=discovery_summary,
    check_function=check_summary,
)
