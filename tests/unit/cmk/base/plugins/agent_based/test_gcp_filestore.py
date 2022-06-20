#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

import pytest

from cmk.base.api.agent_based.checking_classes import ServiceLabel
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.gcp_filestore import check, discover, parse
from cmk.base.plugins.agent_based.utils import gcp

from cmk.special_agents.agent_gcp import FILESTORE

from .gcp_test_util import DiscoverTester, generate_timeseries, ParsingTester, Plugin

ASSET_TABLE = [
    ['{"project":"backup-255820", "config": ["filestore"]}'],
    [
        '{"name": "//file.googleapis.com/projects/tribe29-check-development/locations/us-central1-a/instances/test", "asset_type": "file.googleapis.com/Instance", "resource": {"version": "v1", "discovery_document_uri": "https://file.googleapis.com/$discovery/rest", "discovery_name": "Instance", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {"fileShares":[{"capacityGb": "1024", "name": "test"}], "name": "projects/tribe29-check-development/locations/us-central1-a/instances/test", "createTime": "2022-03-21T08:14:23.899938334Z", "tier": "BASIC_HDD", "labels": {"foo": "bar"}, "state": "READY", "networks": [{"modes": ["MODE_IPV4"], "network": "default", "reservedIpRange": "10.212.4.208/29", "ipAddresses": ["10.212.4.210"], "connectMode": "DIRECT_PEERING"}]}, "location": "us-central1-a", "resource_url": ""}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-03-21T08:18:19.508418Z", "org_policy": []}'
    ],
]


class TestParsing(ParsingTester):
    def parse(self, string_table):
        return parse(string_table)

    @property
    def section_table(self) -> StringTable:
        return generate_timeseries("item", 42.0, FILESTORE)


class TestDiscover(DiscoverTester):
    @property
    def _assets(self) -> StringTable:
        return ASSET_TABLE

    @property
    def expected_services(self) -> set[str]:
        return {"test"}

    @property
    def expected_labels(self) -> set[ServiceLabel]:
        return {
            ServiceLabel("gcp/location", "us-central1-a"),
            ServiceLabel("gcp/filestore/name", "test"),
            ServiceLabel("gcp/projectId", "backup-255820"),
            ServiceLabel("gcp/labels/foo", "bar"),
        }

    def discover(self, assets: Optional[gcp.AssetSection]) -> DiscoveryResult:
        yield from discover(section_gcp_service_filestore=None, section_gcp_assets=assets)


def test_discover_labels_labels_without_user_labels() -> None:
    asset_table = [
        ['{"project":"backup-255820", "config": ["filestore"]}'],
        [
            '{"name": "//file.googleapis.com/projects/tribe29-check-development/locations/us-central1-a/instances/test", "asset_type": "file.googleapis.com/Instance", "resource": {"version": "v1", "discovery_document_uri": "https://file.googleapis.com/$discovery/rest", "discovery_name": "Instance", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {"fileShares":[{"capacityGb": "1024", "name": "test"}], "name": "projects/tribe29-check-development/locations/us-central1-a/instances/test", "createTime": "2022-03-21T08:14:23.899938334Z", "tier": "BASIC_HDD", "labels": {}, "state": "READY", "networks": [{"modes": ["MODE_IPV4"], "network": "default", "reservedIpRange": "10.212.4.208/29", "ipAddresses": ["10.212.4.210"], "connectMode": "DIRECT_PEERING"}]}, "location": "us-central1-a", "resource_url": ""}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-03-21T08:18:19.508418Z", "org_policy": []}'
        ],
    ]
    asset_section = gcp.parse_assets(asset_table)
    servers = list(discover(section_gcp_service_filestore=None, section_gcp_assets=asset_section))
    labels = servers[0].labels
    assert set(labels) == {
        ServiceLabel("gcp/location", "us-central1-a"),
        ServiceLabel("gcp/filestore/name", "test"),
        ServiceLabel("gcp/projectId", "backup-255820"),
    }


PLUGINS = [
    Plugin(
        function=check,
        metrics=["fs_used_percent", "disk_read_ios", "disk_write_ios"],
        results=[
            Result(state=State.OK, summary="Read operations: 42.0"),
            Result(state=State.OK, summary="Usage: 4200.00%"),
            Result(state=State.OK, summary="Write operations: 42.0"),
        ],
    ),
]


def generate_results(plugin: Plugin) -> CheckResult:
    item = "item"
    section = parse(generate_timeseries(item, 42.0, FILESTORE))
    yield from plugin.function(
        item=item,
        params={k: None for k in plugin.metrics},
        section_gcp_service_filestore=section,
        section_gcp_assets=None,
    )


@pytest.mark.parametrize("plugin", PLUGINS)
def test_yield_results_as_specified(plugin) -> None:
    results = {r for r in generate_results(plugin) if isinstance(r, Result)}
    assert results == set(plugin.results)


@pytest.mark.parametrize("plugin", PLUGINS)
def test_yield_metrics_as_specified(plugin) -> None:
    results = {r.name for r in generate_results(plugin) if isinstance(r, Metric)}
    assert results == set(plugin.metrics)
