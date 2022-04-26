#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping, Optional

from .agent_based_api.v1 import register, render, Service, ServiceLabel
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import gcp


def parse_gcp_gcs(string_table: StringTable) -> gcp.Section:
    return gcp.parse_gcp(string_table, "bucket_name")


service_namer = gcp.service_name_factory("GCS")

register.agent_section(name="gcp_service_gcs", parse_function=parse_gcp_gcs)


def discover(
    section_gcp_service_gcs: Optional[gcp.Section], section_gcp_assets: Optional[gcp.AssetSection]
) -> DiscoveryResult:
    if section_gcp_assets is None:
        return
    bucket_type = "storage.googleapis.com/Bucket"
    buckets = [a for a in section_gcp_assets if a.asset.asset_type == bucket_type]
    for bucket in buckets:
        data = bucket.asset.resource.data
        item = data["id"]
        labels = [ServiceLabel(f"gcp/labels/{k}", v) for k, v in data["labels"].items()]
        labels.append(ServiceLabel("gcp/location", data["location"]))
        labels.append(ServiceLabel("gcp/bucket/storageClass", data["storageClass"]))
        labels.append(ServiceLabel("gcp/bucket/locationType", data["locationType"]))
        labels.append(ServiceLabel("gcp/projectId", section_gcp_assets.project))
        yield Service(item=item, labels=labels)


def check_gcp_gcs_requests(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_gcs: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> CheckResult:
    if section_gcp_service_gcs is None:
        return
    metrics = {
        "requests": gcp.MetricSpec("storage.googleapis.com/api/request_count", "requests", str)
    }
    timeseries = section_gcp_service_gcs.get(item, gcp.SectionItem(rows=[])).rows
    yield from gcp.generic_check(metrics, timeseries, params)


register.check_plugin(
    name="gcp_gcs_requests",
    sections=["gcp_service_gcs", "gcp_assets"],
    service_name=service_namer("requests"),
    check_ruleset_name="gcp_gcs_requests",
    discovery_function=discover,
    check_function=check_gcp_gcs_requests,
    check_default_parameters={"requests": None},
)


def check_gcp_gcs_network(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_gcs: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> CheckResult:
    if section_gcp_service_gcs is None:
        return
    metrics = {
        "net_data_sent": gcp.MetricSpec(
            "storage.googleapis.com/network/sent_bytes_count", "Out", render.networkbandwidth
        ),
        "net_data_recv": gcp.MetricSpec(
            "storage.googleapis.com/network/received_bytes_count", "In", render.networkbandwidth
        ),
    }
    timeseries = section_gcp_service_gcs.get(item, gcp.SectionItem(rows=[])).rows
    yield from gcp.generic_check(metrics, timeseries, params)


register.check_plugin(
    name="gcp_gcs_network",
    sections=["gcp_service_gcs", "gcp_assets"],
    service_name=service_namer("networks"),
    check_ruleset_name="gcp_gcs_network",
    discovery_function=discover,
    check_function=check_gcp_gcs_network,
    check_default_parameters={"net_data_sent": None, "net_data_recv": None},
)


def check_gcp_gcs_object(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_gcs: Optional[gcp.Section],
    section_gcp_assets: Optional[gcp.AssetSection],
) -> CheckResult:
    if section_gcp_service_gcs is None:
        return
    metrics = {
        "aws_bucket_size": gcp.MetricSpec(
            "storage.googleapis.com/storage/total_bytes", "Bucket size", render.bytes
        ),
        "aws_num_objects": gcp.MetricSpec(
            "storage.googleapis.com/storage/object_count", "Objects", str
        ),
    }
    timeseries = section_gcp_service_gcs.get(item, gcp.SectionItem(rows=[])).rows
    yield from gcp.generic_check(metrics, timeseries, params)


register.check_plugin(
    name="gcp_gcs_objects",
    sections=["gcp_service_gcs", "gcp_assets"],
    service_name=service_namer("objects"),
    check_ruleset_name="gcp_gcs_objects",
    discovery_function=discover,
    check_function=check_gcp_gcs_object,
    check_default_parameters={"aws_bucket_size": None, "aws_num_objects": None},
)
