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
    Service,
    ServiceLabel,
    StringTable,
)
from cmk.plugins.gcp.lib import gcp
from cmk.plugins.lib.diskstat import check_diskstat_dict_legacy


def parse(string_table: StringTable) -> gcp.Section:
    return gcp.parse_gcp(string_table, gcp.ResourceKey("instance_name"))


agent_section_gcp_service_filestore = AgentSection(
    name="gcp_service_filestore", parse_function=parse
)

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
            ServiceLabel("cmk/gcp/location", share.location),
            ServiceLabel("cmk/gcp/filestore/name", item),
        ]
        labels.extend(
            [ServiceLabel(f"cmk/gcp/labels/{k}", v) for k, v in data.get("labels", {}).items()]
        )
        yield Service(item=item, labels=labels)


def check(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_filestore: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> CheckResult:
    if section_gcp_service_filestore is None or not gcp.item_in_section(
        item, ASSET_TYPE, section_gcp_assets
    ):
        return

    metrics = {
        "utilization": gcp.MetricExtractionSpec(
            "file.googleapis.com/nfs/server/used_bytes_percent"
        ),
        "read_ios": gcp.MetricExtractionSpec("file.googleapis.com/nfs/server/read_ops_count"),
        "write_ios": gcp.MetricExtractionSpec("file.googleapis.com/nfs/server/write_ops_count"),
        "average_read_wait": gcp.MetricExtractionSpec(
            "file.googleapis.com/nfs/server/average_read_latency"
        ),
        "average_write_wait": gcp.MetricExtractionSpec(
            "file.googleapis.com/nfs/server/average_write_latency"
        ),
        "free_capacity": gcp.MetricExtractionSpec("file.googleapis.com/nfs/server/free_bytes"),
        "used_capacity": gcp.MetricExtractionSpec("file.googleapis.com/nfs/server/used_bytes"),
    }

    timeseries = section_gcp_service_filestore.get(item, gcp.SectionItem(rows=[])).rows

    disk_data = {
        metric_name: gcp.get_value(timeseries, metric_spec)
        for metric_name, metric_spec in metrics.items()
    }
    disk_data["capacity"] = disk_data.pop("free_capacity") + disk_data["used_capacity"]

    yield from check_diskstat_dict_legacy(
        params=params,
        disk=disk_data,
        value_store=get_value_store(),
        this_time=time.time(),
    )


check_plugin_gcp_filestore_disk = CheckPlugin(
    name="gcp_filestore_disk",
    sections=["gcp_service_filestore", "gcp_assets"],
    service_name=service_namer("disk"),
    check_ruleset_name="gcp_filestore_disk",
    discovery_function=discover,
    check_function=check,
    check_default_parameters={
        "disk_utilization": (80.0, 90.0),
        "disk_read_ios": None,
        "disk_write_ios": None,
        "disk_average_read_wait": None,
        "disk_average_write_wait": None,
        "latency": None,
    },
)


def discovery_summary(section: gcp.AssetSection) -> DiscoveryResult:
    yield from gcp.discovery_summary(section, "filestore")


def check_summary(section: gcp.AssetSection) -> CheckResult:
    yield from gcp.check_summary(ASSET_TYPE, "Filestore", section)


check_plugin_gcp_filestore_summary = CheckPlugin(
    name="gcp_filestore_summary",
    sections=["gcp_assets"],
    service_name=service_namer.summary_name(),
    discovery_function=discovery_summary,
    check_function=check_summary,
)
