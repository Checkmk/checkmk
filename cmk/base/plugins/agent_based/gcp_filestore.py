#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs
from collections.abc import Mapping
from typing import Any

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, render, Service, ServiceLabel
from cmk.base.plugins.agent_based.utils import gcp

from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


def parse(string_table: StringTable) -> gcp.Section:
    return gcp.parse_gcp(string_table, gcp.ResourceKey("instance_name"))


register.agent_section(name="gcp_service_filestore", parse_function=parse)

service_namer = gcp.service_name_factory("Filestore")
ASSET_TYPE = gcp.AssetType("file.googleapis.com/Instance")


def discover(
    section_gcp_service_filestore: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> DiscoveryResult:
    assets = gcp.validate_asset_section(section_gcp_assets, "filestore")
    for item, share in assets[ASSET_TYPE].items():
        data = share.resource_data
        labels = [
            ServiceLabel("gcp/location", share.location),
            ServiceLabel("gcp/filestore/name", item),
            ServiceLabel("gcp/projectId", assets.project),
        ]
        labels.extend([ServiceLabel(f"gcp/labels/{k}", v) for k, v in data["labels"].items()])
        yield Service(item=item, labels=labels)


def check(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_filestore: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> CheckResult:
    metrics = {
        "fs_used_percent": gcp.MetricSpec(
            "file.googleapis.com/nfs/server/used_bytes_percent", "Usage", render.percent, scale=1e2
        ),
        "disk_read_ios": gcp.MetricSpec(
            "file.googleapis.com/nfs/server/read_ops_count", "Read operations", str
        ),
        "disk_write_ios": gcp.MetricSpec(
            "file.googleapis.com/nfs/server/write_ops_count", "Write operations", str
        ),
    }
    yield from gcp.check(
        metrics, item, params, section_gcp_service_filestore, ASSET_TYPE, section_gcp_assets
    )


register.check_plugin(
    name="gcp_filestore_disk",
    sections=["gcp_service_filestore", "gcp_assets"],
    service_name=service_namer("disk"),
    check_ruleset_name="gcp_filestore_disk",
    discovery_function=discover,
    check_function=check,
    check_default_parameters={
        "fs_used_percent": (80.0, 90.0),
        "disk_read_ios": None,
        "disk_write_ios": None,
    },
)


def discovery_summary(section: gcp.AssetSection) -> DiscoveryResult:
    yield from gcp.discovery_summary(section, "filestore")


def check_summary(section: gcp.AssetSection) -> CheckResult:
    yield from gcp.check_summary(ASSET_TYPE, "Filestore", section)


register.check_plugin(
    name="gcp_filestore_summary",
    sections=["gcp_assets"],
    service_name=service_namer.summary_name(),
    discovery_function=discovery_summary,
    check_function=check_summary,
)
