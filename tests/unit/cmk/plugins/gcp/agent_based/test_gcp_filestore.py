#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs


import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    ServiceLabel,
    State,
    StringTable,
)
from cmk.plugins.gcp.agent_based.gcp_assets import parse_assets
from cmk.plugins.gcp.agent_based.gcp_filestore import check, check_summary, discover, parse
from cmk.plugins.gcp.lib import gcp
from cmk.plugins.gcp.special_agents.agent_gcp import FILESTORE

from .gcp_test_util import DiscoverTester, generate_stringtable, Plugin

ASSET_TABLE = [
    [f'{{"project":"backup-255820", "config": ["{FILESTORE.name}"]}}'],
    [
        '{"name": "//file.googleapis.com/projects/checkmk-check-development/locations/us-central1-a/instances/test", "asset_type": "file.googleapis.com/Instance", "resource": {"version": "v1", "discovery_document_uri": "https://file.googleapis.com/$discovery/rest", "discovery_name": "Instance", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {"fileShares":[{"capacityGb": "1024", "name": "test"}], "name": "projects/checkmk-check-development/locations/us-central1-a/instances/test", "createTime": "2022-03-21T08:14:23.899938334Z", "tier": "BASIC_HDD", "labels": {"foo": "bar"}, "state": "READY", "networks": [{"modes": ["MODE_IPV4"], "network": "default", "reservedIpRange": "10.212.4.208/29", "ipAddresses": ["10.212.4.210"], "connectMode": "DIRECT_PEERING"}]}, "location": "us-central1-a", "resource_url": ""}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-03-21T08:18:19.508418Z", "org_policy": []}'
    ],
]


class TestDiscover(DiscoverTester):
    @property
    def _assets(self) -> StringTable:
        return ASSET_TABLE

    @property
    def expected_items(self) -> set[str]:
        return {"test"}

    @property
    def expected_labels(self) -> set[ServiceLabel]:
        return {
            ServiceLabel("cmk/gcp/location", "us-central1-a"),
            ServiceLabel("cmk/gcp/filestore/name", "test"),
            ServiceLabel("cmk/gcp/labels/foo", "bar"),
        }

    def discover(self, assets: gcp.AssetSection | None) -> DiscoveryResult:
        yield from discover(section_gcp_service_filestore=None, section_gcp_assets=assets)


def test_discover_labels_labels_without_user_labels() -> None:
    asset_table = [
        ['{"project":"backup-255820", "config": ["filestore"]}'],
        [
            '{"name": "//file.googleapis.com/projects/checkmk-check-development/locations/us-central1-a/instances/test", "asset_type": "file.googleapis.com/Instance", "resource": {"version": "v1", "discovery_document_uri": "https://file.googleapis.com/$discovery/rest", "discovery_name": "Instance", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {"fileShares":[{"capacityGb": "1024", "name": "test"}], "name": "projects/checkmk-check-development/locations/us-central1-a/instances/test", "createTime": "2022-03-21T08:14:23.899938334Z", "tier": "BASIC_HDD", "state": "READY", "networks": [{"modes": ["MODE_IPV4"], "network": "default", "reservedIpRange": "10.212.4.208/29", "ipAddresses": ["10.212.4.210"], "connectMode": "DIRECT_PEERING"}]}, "location": "us-central1-a", "resource_url": ""}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-03-21T08:18:19.508418Z", "org_policy": []}'
        ],
    ]
    asset_section = parse_assets(asset_table)
    servers = list(discover(section_gcp_service_filestore=None, section_gcp_assets=asset_section))
    labels = servers[0].labels
    assert set(labels) == {
        ServiceLabel("cmk/gcp/location", "us-central1-a"),
        ServiceLabel("cmk/gcp/filestore/name", "test"),
    }


PLUGINS = [
    Plugin(
        function=check,
        metrics=[
            "disk_utilization",
            "disk_read_ios",
            "disk_write_ios",
            "disk_average_read_wait",
            "disk_average_write_wait",
            "disk_latency",
        ],
        pure_metrics=["disk_used_capacity", "disk_capacity"],
        results=[
            Result(state=State.OK, notice="Utilization: 4200.00%"),
            Result(state=State.OK, notice="Read operations: 42.00/s"),
            Result(state=State.OK, notice="Write operations: 42.00/s"),
            Result(state=State.OK, notice="Average read wait: 42 seconds"),
            Result(state=State.OK, notice="Average write wait: 42 seconds"),
        ],
        additional_results=[
            Result(state=State.OK, summary="Latency: 42 seconds"),
        ],
    ),
]


def generate_results(plugin: Plugin) -> CheckResult:
    item = "item"
    asset_table = [
        [f'{{"project":"backup-255820", "config": ["{FILESTORE.name}"]}}'],
        [
            f'{{"name": "//file.googleapis.com/projects/checkmk-check-development/locations/us-central1-a/instances/test", "asset_type": "file.googleapis.com/Instance", "resource": {{"version": "v1", "discovery_document_uri": "https://file.googleapis.com/$discovery/rest", "discovery_name": "Instance", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {{"fileShares":[{{"capacityGb": "1024", "name": "test"}}], "name": "projects/checkmk-check-development/locations/us-central1-a/instances/{item}", "createTime": "2022-03-21T08:14:23.899938334Z", "tier": "BASIC_HDD", "labels": {{}}, "state": "READY", "networks": [{{"modes": ["MODE_IPV4"], "network": "default", "reservedIpRange": "10.212.4.208/29", "ipAddresses": ["10.212.4.210"], "connectMode": "DIRECT_PEERING"}}]}}, "location": "us-central1-a", "resource_url": ""}}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-03-21T08:18:19.508418Z", "org_policy": []}}'
        ],
    ]
    section = parse(generate_stringtable(item, 42.0, FILESTORE))
    yield from plugin.function(
        item=item,
        params={k: None for k in plugin.metrics},
        section_gcp_service_filestore=section,
        section_gcp_assets=parse_assets(asset_table),
    )


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize("plugin", PLUGINS)
def test_yield_results_as_specified(plugin: Plugin) -> None:
    results = {r for r in generate_results(plugin) if isinstance(r, Result)}
    assert results == plugin.expected_results()


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize("plugin", PLUGINS)
def test_yield_metrics_as_specified(plugin: Plugin) -> None:
    results = {r.name for r in generate_results(plugin) if isinstance(r, Metric)}
    assert results == plugin.expected_metrics()


def test_check_summary() -> None:
    assets = parse_assets(ASSET_TABLE)
    results = set(check_summary(section=assets))
    assert results == {Result(state=State.OK, summary="1 Filestore", details="Found 1 filestore")}
