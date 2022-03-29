#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping, Optional

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, render, Service, ServiceLabel
from cmk.base.plugins.agent_based.utils import gcp

from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


def parse(string_table: StringTable) -> gcp.Section:
    return gcp.parse_gcp(string_table, "instance_name")


register.agent_section(name="gcp_service_filestore", parse_function=parse)


def discover(
    section_gcp_service_filestore: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> DiscoveryResult:
    if section_gcp_assets is None:
        return
    asset_type = "file.googleapis.com/Instance"
    shares = [a for a in section_gcp_assets if a.asset.asset_type == asset_type]
    for share in shares:
        data = share.asset.resource.data
        item = data["name"].split("/")[-1]
        labels = [
            ServiceLabel("gcp/location", share.asset.resource.location),
            ServiceLabel("gcp/filestore/name", item),
            ServiceLabel("gcp/projectId", section_gcp_assets.project),
        ]
        labels.extend([ServiceLabel(f"gcp/labels/{k}", v) for k, v in data["labels"].items()])
        yield Service(item=item, labels=labels)


def check(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_filestore: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> CheckResult:
    if section_gcp_service_filestore is None:
        return
    section = section_gcp_service_filestore
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
    timeseries = section[item].rows
    yield from gcp.generic_check(metrics, timeseries, params)


register.check_plugin(
    name="gcp_filestore_disk",
    sections=["gcp_service_filestore", "gcp_assets"],
    service_name="GCP Filestore %s",
    check_ruleset_name="gcp_filestore_disk",
    discovery_function=discover,
    check_function=check,
    check_default_parameters={},
)
