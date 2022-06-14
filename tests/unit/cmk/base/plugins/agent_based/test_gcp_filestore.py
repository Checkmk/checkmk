#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Callable, Optional, Sequence

import pytest
from pytest_mock import MockerFixture

from cmk.utils.type_defs import CheckPluginName

from cmk.base.api.agent_based.checking_classes import ServiceLabel
from cmk.base.plugin_contexts import current_host, current_service
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import DiscoveryResult, StringTable
from cmk.base.plugins.agent_based.gcp_filestore import check, discover, parse
from cmk.base.plugins.agent_based.utils import gcp

from .gcp_test_util import DiscoverTester, ParsingTester

SECTION_TABLE = [
    [
        '{"metric": {"type": "file.googleapis.com/nfs/server/used_bytes_percent", "labels": {}}, "resource": {"type": "filestore_instance", "labels": {"project_id": "tribe29-check-development", "instance_name": "test"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-03-21T09:01:53.311694Z", "end_time": "2022-03-21T09:01:53.311694Z"}, "value": {"double_value": 2.6521106519794557e-06}}, {"interval": {"start_time": "2022-03-21T09:00:53.311694Z", "end_time": "2022-03-21T09:00:53.311694Z"}, "value": {"double_value": 2.6521106519794557e-06}}, {"interval": {"start_time": "2022-03-21T08:59:53.311694Z", "end_time": "2022-03-21T08:59:53.311694Z"}, "value": {"double_value": 2.6521106519794557e-06}}, {"interval": {"start_time": "2022-03-21T08:58:53.311694Z", "end_time": "2022-03-21T08:58:53.311694Z"}, "value": {"double_value": 2.6521106519794557e-06}}, {"interval": {"start_time": "2022-03-21T08:57:53.311694Z", "end_time": "2022-03-21T08:57:53.311694Z"}, "value": {"double_value": 2.6521106519794557e-06}}, {"interval": {"start_time": "2022-03-21T08:56:53.311694Z", "end_time": "2022-03-21T08:56:53.311694Z"}, "value": {"double_value": 2.6521106519794557e-06}}, {"interval": {"start_time": "2022-03-21T08:55:53.311694Z", "end_time": "2022-03-21T08:55:53.311694Z"}, "value": {"double_value": 2.6521106519794557e-06}}, {"interval": {"start_time": "2022-03-21T08:54:53.311694Z", "end_time": "2022-03-21T08:54:53.311694Z"}, "value": {"double_value": 2.6521106519794557e-06}}, {"interval": {"start_time": "2022-03-21T08:53:53.311694Z", "end_time": "2022-03-21T08:53:53.311694Z"}, "value": {"double_value": 2.6521106519794557e-06}}, {"interval": {"start_time": "2022-03-21T08:52:53.311694Z", "end_time": "2022-03-21T08:52:53.311694Z"}, "value": {"double_value": 2.6521106519794557e-06}}, {"interval": {"start_time": "2022-03-21T08:51:53.311694Z", "end_time": "2022-03-21T08:51:53.311694Z"}, "value":{"double_value": 2.6521106519794557e-06}}, {"interval": {"start_time": "2022-03-21T08:50:53.311694Z", "end_time": "2022-03-21T08:50:53.311694Z"}, "value": {"double_value": 2.6521106519794557e-06}}, {"interval": {"start_time": "2022-03-21T08:49:53.311694Z", "end_time": "2022-03-21T08:49:53.311694Z"}, "value": {"double_value": 2.6521106519794557e-06}}, {"interval": {"start_time": "2022-03-21T08:48:53.311694Z", "end_time": "2022-03-21T08:48:53.311694Z"}, "value": {"double_value": 2.6521106519794557e-06}}, {"interval": {"start_time": "2022-03-21T08:47:53.311694Z", "end_time": "2022-03-21T08:47:53.311694Z"}, "value": {"double_value": 2.6521106519794557e-06}}, {"interval": {"start_time": "2022-03-21T08:46:53.311694Z", "end_time": "2022-03-21T08:46:53.311694Z"}, "value": {"double_value": 2.6521106519794557e-06}}, {"interval": {"start_time": "2022-03-21T08:45:53.311694Z", "end_time": "2022-03-21T08:45:53.311694Z"}, "value": {"double_value": 2.6521106519794557e-06}}, {"interval": {"start_time": "2022-03-21T08:44:53.311694Z", "end_time": "2022-03-21T08:44:53.311694Z"}, "value": {"double_value": 2.6521106519794557e-06}}, {"interval": {"start_time": "2022-03-21T08:43:53.311694Z", "end_time": "2022-03-21T08:43:53.311694Z"}, "value": {"double_value": 2.6521106519794557e-06}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "file.googleapis.com/nfs/server/write_ops_count", "labels": {}}, "resource": {"type": "filestore_instance", "labels": {"instance_name": "test", "project_id": "tribe29-check-development"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-03-21T09:01:53.311694Z", "end_time": "2022-03-21T09:01:53.311694Z"}, "value": {"double_value":0.1}}, {"interval": {"start_time": "2022-03-21T09:00:53.311694Z", "end_time": "2022-03-21T09:00:53.311694Z"}, "value": {"double_value": 0.1}}, {"interval": {"start_time": "2022-03-21T08:59:53.311694Z", "end_time": "2022-03-21T08:59:53.311694Z"}, "value": {"double_value": 0.1}}, {"interval": {"start_time": "2022-03-21T08:58:53.311694Z", "end_time": "2022-03-21T08:58:53.311694Z"}, "value": {"double_value": 0.1}}, {"interval": {"start_time": "2022-03-21T08:57:53.311694Z", "end_time": "2022-03-21T08:57:53.311694Z"}, "value": {"double_value": 0.1}}, {"interval": {"start_time": "2022-03-21T08:56:53.311694Z", "end_time": "2022-03-21T08:56:53.311694Z"}, "value": {"double_value": 0.1}}, {"interval": {"start_time": "2022-03-21T08:55:53.311694Z", "end_time": "2022-03-21T08:55:53.311694Z"}, "value": {"double_value": 0.1}}, {"interval": {"start_time": "2022-03-21T08:54:53.311694Z", "end_time": "2022-03-21T08:54:53.311694Z"}, "value": {"double_value": 0.1}}, {"interval": {"start_time": "2022-03-21T08:53:53.311694Z", "end_time": "2022-03-21T08:53:53.311694Z"}, "value": {"double_value": 0.1}}, {"interval": {"start_time": "2022-03-21T08:52:53.311694Z", "end_time": "2022-03-21T08:52:53.311694Z"}, "value": {"double_value": 0.1}}, {"interval": {"start_time": "2022-03-21T08:51:53.311694Z", "end_time": "2022-03-21T08:51:53.311694Z"}, "value": {"double_value": 0.1}}, {"interval": {"start_time": "2022-03-21T08:50:53.311694Z", "end_time": "2022-03-21T08:50:53.311694Z"}, "value": {"double_value": 0.1}}, {"interval": {"start_time": "2022-03-21T08:49:53.311694Z", "end_time": "2022-03-21T08:49:53.311694Z"}, "value": {"double_value": 0.1}}, {"interval": {"start_time": "2022-03-21T08:48:53.311694Z", "end_time": "2022-03-21T08:48:53.311694Z"}, "value": {"double_value": 0.1}}, {"interval": {"start_time": "2022-03-21T08:47:53.311694Z", "end_time": "2022-03-21T08:47:53.311694Z"}, "value": {"double_value": 0.1}}, {"interval": {"start_time": "2022-03-21T08:46:53.311694Z", "end_time": "2022-03-21T08:46:53.311694Z"}, "value": {"double_value": 0.1}}, {"interval": {"start_time": "2022-03-21T08:45:53.311694Z", "end_time": "2022-03-21T08:45:53.311694Z"}, "value": {"double_value": 0.1}}, {"interval": {"start_time": "2022-03-21T08:44:53.311694Z", "end_time": "2022-03-21T08:44:53.311694Z"}, "value": {"double_value": 0.1}}, {"interval": {"start_time": "2022-03-21T08:43:53.311694Z", "end_time": "2022-03-21T08:43:53.311694Z"}, "value": {"double_value": 0.1}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "file.googleapis.com/nfs/server/read_ops_count", "labels": {}}, "resource": {"type": "filestore_instance", "labels": {"instance_name": "test", "project_id": "tribe29-check-development"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-03-21T09:01:53.311694Z", "end_time": "2022-03-21T09:01:53.311694Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-21T09:00:53.311694Z", "end_time": "2022-03-21T09:00:53.311694Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-21T08:59:53.311694Z", "end_time": "2022-03-21T08:59:53.311694Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-21T08:58:53.311694Z", "end_time": "2022-03-21T08:58:53.311694Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-21T08:57:53.311694Z", "end_time": "2022-03-21T08:57:53.311694Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-21T08:56:53.311694Z", "end_time": "2022-03-21T08:56:53.311694Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-21T08:55:53.311694Z", "end_time": "2022-03-21T08:55:53.311694Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-21T08:54:53.311694Z", "end_time": "2022-03-21T08:54:53.311694Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-21T08:53:53.311694Z", "end_time": "2022-03-21T08:53:53.311694Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-21T08:52:53.311694Z", "end_time": "2022-03-21T08:52:53.311694Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-21T08:51:53.311694Z", "end_time": "2022-03-21T08:51:53.311694Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-21T08:50:53.311694Z", "end_time": "2022-03-21T08:50:53.311694Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-21T08:49:53.311694Z", "end_time": "2022-03-21T08:49:53.311694Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-21T08:48:53.311694Z", "end_time": "2022-03-21T08:48:53.311694Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-21T08:47:53.311694Z", "end_time": "2022-03-21T08:47:53.311694Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-21T08:46:53.311694Z", "end_time": "2022-03-21T08:46:53.311694Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-21T08:45:53.311694Z", "end_time": "2022-03-21T08:45:53.311694Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-21T08:44:53.311694Z", "end_time": "2022-03-21T08:44:53.311694Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-03-21T08:43:53.311694Z", "end_time": "2022-03-21T08:43:53.311694Z"}, "value": {"double_value": 0.0}}], "unit": ""}'
    ],
]

ASSET_TABLE = [
    ['{"project":"backup-255820"}'],
    [
        '{"name": "//file.googleapis.com/projects/tribe29-check-development/locations/us-central1-a/instances/test", "asset_type": "file.googleapis.com/Instance", "resource": {"version": "v1", "discovery_document_uri": "https://file.googleapis.com/$discovery/rest", "discovery_name": "Instance", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {"fileShares":[{"capacityGb": "1024", "name": "test"}], "name": "projects/tribe29-check-development/locations/us-central1-a/instances/test", "createTime": "2022-03-21T08:14:23.899938334Z", "tier": "BASIC_HDD", "labels": {"foo": "bar"}, "state": "READY", "networks": [{"modes": ["MODE_IPV4"], "network": "default", "reservedIpRange": "10.212.4.208/29", "ipAddresses": ["10.212.4.210"], "connectMode": "DIRECT_PEERING"}]}, "location": "us-central1-a", "resource_url": ""}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-03-21T08:18:19.508418Z", "org_policy": []}'
    ],
]


class TestParsing(ParsingTester):
    def parse(self, string_table):
        return parse(string_table)

    @property
    def section_table(self) -> StringTable:
        return SECTION_TABLE


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
        ['{"project":"backup-255820"}'],
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


@dataclass(frozen=True)
class Plugin:
    metrics: Sequence[str]
    function: Callable


PLUGINS = [
    Plugin(
        function=check,
        metrics=["fs_used_percent", "disk_read_ios", "disk_write_ios"],
    ),
]
ITEM = "test"


@pytest.fixture(name="section")
def fixture_section():
    return parse(SECTION_TABLE)


@pytest.fixture(params=PLUGINS, name="checkplugin")
def fixture_checkplugin(request):
    return request.param


@pytest.fixture(
    params=[None, {"levels_upper": (0, 1), "horizon": 1, "period": "day"}], name="params"
)
def fixture_params(request):
    return request.param


@pytest.fixture(name="results")
def fixture_results(checkplugin, section, params, mocker: MockerFixture):
    params = {k: params for k in checkplugin.metrics}
    mocker.patch(
        "cmk.base.check_api._prediction.get_levels", return_value=(None, (2.2, 4.2, None, None))
    )

    with current_host("unittest"), current_service(
        CheckPluginName("test_check"), "unittest-service-description"
    ):
        results = list(
            checkplugin.function(
                item=ITEM,
                params=params,
                section_gcp_service_filestore=section,
                section_gcp_assets=None,
            )
        )
    return results, checkplugin


def test_no_function_section_yields_no_metric_data(checkplugin) -> None:
    params = {k: None for k in checkplugin.metrics}
    results = list(
        checkplugin.function(
            item=ITEM,
            params=params,
            section_gcp_service_filestore=None,
            section_gcp_assets=None,
        )
    )
    assert len(results) == 0


def test_yield_metrics_as_specified(results) -> None:
    results, checkplugin = results
    res = {r.name: r for r in results if isinstance(r, Metric)}
    assert len(res) == len(checkplugin.metrics)
    assert set(res.keys()) == set(checkplugin.metrics)


def test_yield_results_as_specified(results) -> None:
    results, checkplugin = results
    res = [r for r in results if isinstance(r, Result)]
    assert len(res) == len(checkplugin.metrics)
    for r in res:
        assert r.state == State.OK
