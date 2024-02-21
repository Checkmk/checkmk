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


def parse_gcp_gcs(string_table: StringTable) -> gcp.Section:
    return gcp.parse_gcp(string_table, gcp.ResourceKey("bucket_name"))


agent_section_gcp_service_gcs = AgentSection(name="gcp_service_gcs", parse_function=parse_gcp_gcs)


service_namer = gcp.service_name_factory("GCS")
SECTIONS = ["gcp_service_gcs", "gcp_assets"]
ASSET_TYPE = gcp.AssetType("storage.googleapis.com/Bucket")


def discover(
    section_gcp_service_gcs: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> DiscoveryResult:
    assets = gcp.validate_asset_section(section_gcp_assets, "gcs")
    for item, bucket in assets[ASSET_TYPE].items():
        data = bucket.resource_data
        labels = [ServiceLabel(f"cmk/gcp/labels/{k}", v) for k, v in data["labels"].items()]
        labels.append(ServiceLabel("cmk/gcp/location", data["location"]))
        labels.append(ServiceLabel("cmk/gcp/bucket/storageClass", data["storageClass"]))
        labels.append(ServiceLabel("cmk/gcp/bucket/locationType", data["locationType"]))
        yield Service(item=item, labels=labels)


def check_gcp_gcs_requests(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_gcs: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> CheckResult:
    metrics = {
        "requests": gcp.MetricSpec(
            gcp.MetricExtractionSpec(metric_type="storage.googleapis.com/api/request_count"),
            gcp.MetricDisplaySpec(label="Requests", render_func=str),
        )
    }
    yield from gcp.check(
        metrics, item, params, section_gcp_service_gcs, ASSET_TYPE, section_gcp_assets
    )


check_plugin_gcp_gcs_requests = CheckPlugin(
    name="gcp_gcs_requests",
    sections=SECTIONS,
    service_name=service_namer("requests"),
    check_ruleset_name="gcp_gcs_requests",
    discovery_function=discover,
    check_function=check_gcp_gcs_requests,
    check_default_parameters={"requests": None},
)


def check_gcp_gcs_network(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_gcs: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> CheckResult:
    metrics = {
        "net_data_sent": gcp.MetricSpec(
            gcp.MetricExtractionSpec(metric_type="storage.googleapis.com/network/sent_bytes_count"),
            gcp.MetricDisplaySpec(label="Out", render_func=render.networkbandwidth),
        ),
        "net_data_recv": gcp.MetricSpec(
            gcp.MetricExtractionSpec(
                metric_type="storage.googleapis.com/network/received_bytes_count",
            ),
            gcp.MetricDisplaySpec(label="In", render_func=render.networkbandwidth),
        ),
    }
    yield from gcp.check(
        metrics, item, params, section_gcp_service_gcs, ASSET_TYPE, section_gcp_assets
    )


check_plugin_gcp_gcs_network = CheckPlugin(
    name="gcp_gcs_network",
    sections=SECTIONS,
    service_name=service_namer("networks"),
    check_ruleset_name="gcp_gcs_network",
    discovery_function=discover,
    check_function=check_gcp_gcs_network,
    check_default_parameters={"net_data_sent": None, "net_data_recv": None},
)


def check_gcp_gcs_object(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_gcs: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> CheckResult:
    metrics = {
        "aws_bucket_size": gcp.MetricSpec(
            gcp.MetricExtractionSpec(metric_type="storage.googleapis.com/storage/total_bytes"),
            gcp.MetricDisplaySpec(label="Bucket size", render_func=render.bytes),
        ),
        "aws_num_objects": gcp.MetricSpec(
            gcp.MetricExtractionSpec(metric_type="storage.googleapis.com/storage/object_count"),
            gcp.MetricDisplaySpec(label="Objects", render_func=str),
        ),
    }
    yield from gcp.check(
        metrics, item, params, section_gcp_service_gcs, ASSET_TYPE, section_gcp_assets
    )


check_plugin_gcp_gcs_objects = CheckPlugin(
    name="gcp_gcs_objects",
    sections=SECTIONS,
    service_name=service_namer("objects"),
    check_ruleset_name="gcp_gcs_objects",
    discovery_function=discover,
    check_function=check_gcp_gcs_object,
    check_default_parameters={"aws_bucket_size": None, "aws_num_objects": None},
)


def discovery_summary(section: gcp.AssetSection) -> DiscoveryResult:
    yield from gcp.discovery_summary(section, "gcs")


def check_summary(section: gcp.AssetSection) -> CheckResult:
    yield from gcp.check_summary(ASSET_TYPE, "Bucket", section)


check_plugin_gcp_gcs_summary = CheckPlugin(
    name="gcp_gcs_summary",
    sections=["gcp_assets"],
    service_name=service_namer.summary_name(),
    discovery_function=discovery_summary,
    check_function=check_summary,
)
