#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Callable, Sequence

import pytest

from cmk.base.api.agent_based.checking_classes import Service, ServiceLabel
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.gcp_gcs import (
    check_gcp_gcs_network,
    check_gcp_gcs_object,
    check_gcp_gcs_requests,
    discover,
    parse_gcp_gcs,
)
from cmk.base.plugins.agent_based.utils import gcp

SECTION_TABLE = [
    [
        '{"metric":{"type":"storage.googleapis.com/storage/total_bytes","labels":{}},"resource":{"type":"gcs_bucket","labels":{"bucket_name":"backup-home-ml-free","project_id":"backup-255820"}},"metricKind":1,"valueType":3,"points":[{"interval":{"startTime":"2022-02-23T12:20:54.726496Z","endTime":"2022-02-23T12:20:54.726496Z"},"value":{"doubleValue":3298633360.0}},{"interval":{"startTime":"2022-02-23T12:15:54.726496Z","endTime":"2022-02-23T12:15:54.726496Z"},"value":{"doubleValue":3298633360.0}},{"interval":{"startTime":"2022-02-23T12:10:54.726496Z","endTime":"2022-02-23T12:10:54.726496Z"},"value":{"doubleValue":3298633360.0}}],"unit":""}'
    ],
    [
        '{"metric":{"type":"storage.googleapis.com/storage/total_bytes","labels":{}},"resource":{"type":"gcs_bucket","labels":{"bucket_name":"gcf-sources-360989076580-us-central1","project_id":"backup-255820"}},"metricKind":1,"valueType":3,"points":[{"interval":{"startTime":"2022-02-23T12:20:54.726496Z","endTime":"2022-02-23T12:20:54.726496Z"},"value":{"doubleValue":2075.0}},{"interval":{"startTime":"2022-02-23T12:15:54.726496Z","endTime":"2022-02-23T12:15:54.726496Z"},"value":{"doubleValue":2075.0}},{"interval":{"startTime":"2022-02-23T12:10:54.726496Z","endTime":"2022-02-23T12:10:54.726496Z"},"value":{"doubleValue":2075.0}}],"unit":""}'
    ],
    [
        '{"metric":{"type":"storage.googleapis.com/storage/total_bytes","labels":{}},"resource":{"type":"gcs_bucket","labels":{"bucket_name":"lakjsdklasjd","project_id":"backup-255820"}},"metricKind":1,"valueType":3,"points":[{"interval":{"startTime":"2022-02-23T12:20:54.726496Z","endTime":"2022-02-23T12:20:54.726496Z"},"value":{"doubleValue":2635285452.0}},{"interval":{"startTime":"2022-02-23T12:15:54.726496Z","endTime":"2022-02-23T12:15:54.726496Z"},"value":{"doubleValue":2635285452.0}},{"interval":{"startTime":"2022-02-23T12:10:54.726496Z","endTime":"2022-02-23T12:10:54.726496Z"},"value":{"doubleValue":2635285452.0}}],"unit":""}'
    ],
    [
        '{"metric":{"type":"storage.googleapis.com/storage/total_bytes","labels":{}},"resource":{"type":"gcs_bucket","labels":{"project_id":"backup-255820","bucket_name":"us.artifacts.backup-255820.appspot.com"}},"metricKind":1,"valueType":3,"points":[{"interval":{"startTime":"2022-02-23T12:20:54.726496Z","endTime":"2022-02-23T12:20:54.726496Z"},"value":{"doubleValue":1138733197.0}},{"interval":{"startTime":"2022-02-23T12:15:54.726496Z","endTime":"2022-02-23T12:15:54.726496Z"},"value":{"doubleValue":1138733197.0}},{"interval":{"startTime":"2022-02-23T12:10:54.726496Z","endTime":"2022-02-23T12:10:54.726496Z"},"value":{"doubleValue":1138733197.0}}],"unit":""}'
    ],
    [
        '{"metric":{"type":"storage.googleapis.com/storage/object_count","labels":{}},"resource":{"type":"gcs_bucket","labels":{"bucket_name":"backup-home-ml-free","project_id":"backup-255820"}},"metricKind":1,"valueType":3,"points":[{"interval":{"startTime":"2022-02-23T12:20:54.726496Z","endTime":"2022-02-23T12:20:54.726496Z"},"value":{"doubleValue":4.0}},{"interval":{"startTime":"2022-02-23T12:15:54.726496Z","endTime":"2022-02-23T12:15:54.726496Z"},"value":{"doubleValue":4.0}},{"interval":{"startTime":"2022-02-23T12:10:54.726496Z","endTime":"2022-02-23T12:10:54.726496Z"},"value":{"doubleValue":4.0}}],"unit":""}'
    ],
    [
        '{"metric":{"type":"storage.googleapis.com/storage/object_count","labels":{}},"resource":{"type":"gcs_bucket","labels":{"bucket_name":"gcf-sources-360989076580-us-central1","project_id":"backup-255820"}},"metricKind":1,"valueType":3,"points":[{"interval":{"startTime":"2022-02-23T12:20:54.726496Z","endTime":"2022-02-23T12:20:54.726496Z"},"value":{"doubleValue":4.0}},{"interval":{"startTime":"2022-02-23T12:15:54.726496Z","endTime":"2022-02-23T12:15:54.726496Z"},"value":{"doubleValue":4.0}},{"interval":{"startTime":"2022-02-23T12:10:54.726496Z","endTime":"2022-02-23T12:10:54.726496Z"},"value":{"doubleValue":4.0}}],"unit":""}'
    ],
    [
        '{"metric":{"type":"storage.googleapis.com/storage/object_count","labels":{}},"resource":{"type":"gcs_bucket","labels":{"bucket_name":"lakjsdklasjd","project_id":"backup-255820"}},"metricKind":1,"valueType":3,"points":[{"interval":{"startTime":"2022-02-23T12:20:54.726496Z","endTime":"2022-02-23T12:20:54.726496Z"},"value":{"doubleValue":2.0}},{"interval":{"startTime":"2022-02-23T12:15:54.726496Z","endTime":"2022-02-23T12:15:54.726496Z"},"value":{"doubleValue":2.0}},{"interval":{"startTime":"2022-02-23T12:10:54.726496Z","endTime":"2022-02-23T12:10:54.726496Z"},"value":{"doubleValue":2.0}}],"unit":""}'
    ],
    [
        '{"metric":{"type":"storage.googleapis.com/storage/object_count","labels":{}},"resource":{"type":"gcs_bucket","labels":{"project_id":"backup-255820","bucket_name":"us.artifacts.backup-255820.appspot.com"}},"metricKind":1,"valueType":3,"points":[{"interval":{"startTime":"2022-02-23T12:20:54.726496Z","endTime":"2022-02-23T12:20:54.726496Z"},"value":{"doubleValue":88.0}},{"interval":{"startTime":"2022-02-23T12:15:54.726496Z","endTime":"2022-02-23T12:15:54.726496Z"},"value":{"doubleValue":88.0}},{"interval":{"startTime":"2022-02-23T12:10:54.726496Z","endTime":"2022-02-23T12:10:54.726496Z"},"value":{"doubleValue":88.0}}],"unit":""}'
    ],
]

ASSET_TABLE = [
    ['{"project":"backup-255820"}'],
    [
        '{"name": "//storage.googleapis.com/backup-home-ml-free", "asset_type": "storage.googleapis.com/Bucket", "resource": {"version": "v1", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/storage/v1/rest", "discovery_name": "Bucket", "parent": "//cloudresourcemanager.googleapis.com/projects/360989076580", "data": {"name": "backup-home-ml-free", "id": "backup-home-ml-free", "labels": {"tag": "freebackup"}, "projectNumber": 360989076580.0, "timeCreated": "2019-11-03T13:48:57.905Z", "lifecycle": {"rule": []}, "metageneration": 1.0, "cors": [], "storageClass": "STANDARD", "etag": "CAE=", "kind": "storage#bucket", "billing": {}, "versioning": {}, "iamConfiguration": {"uniformBucketLevelAccess": {"enabled": false}, "bucketPolicyOnly": {"enabled": false}}, "owner": {}, "encryption": {}, "updated": "2019-11-03T13:48:57.905Z", "locationType": "region", "logging": {}, "acl": [], "retentionPolicy": {}, "defaultObjectAcl": [], "location": "US-CENTRAL1", "selfLink": "https://www.googleapis.com/storage/v1/b/backup-home-ml-free", "website": {}, "autoclass": {}}, "location": "us-central1", "resource_url": ""}, "ancestors": ["projects/360989076580"], "update_time": "2021-09-20T20:35:59.747Z", "org_policy": []}'
    ],
    [
        '{"name": "//storage.googleapis.com/gcf-sources-360989076580-us-central1", "asset_type": "storage.googleapis.com/Bucket", "resource": {"version": "v1", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/storage/v1/rest", "discovery_name": "Bucket", "parent": "//cloudresourcemanager.googleapis.com/projects/360989076580", "data": {"storageClass": "STANDARD", "owner": {}, "selfLink": "https://www.googleapis.com/storage/v1/b/gcf-sources-360989076580-us-central1", "location": "US-CENTRAL1", "metageneration": 1.0, "updated": "2022-02-07T20:35:50.128Z", "locationType": "region", "lifecycle": {"rule": []}, "versioning": {}, "defaultObjectAcl": [], "billing": {}, "id": "gcf-sources-360989076580-us-central1", "retentionPolicy": {}, "labels": {}, "etag": "CAE=", "website": {}, "iamConfiguration": {"publicAccessPrevention": "inherited", "bucketPolicyOnly": {"enabled": true, "lockedTime": "2022-05-08T20:35:50.128Z"}, "uniformBucketLevelAccess": {"lockedTime": "2022-05-08T20:35:50.128Z", "enabled": true}}, "autoclass": {}, "kind": "storage#bucket", "name": "gcf-sources-360989076580-us-central1", "logging": {}, "acl": [], "timeCreated": "2022-02-07T20:35:50.128Z", "projectNumber": 360989076580.0, "encryption": {}, "cors": [{"origin": ["https://*.cloud.google.com", "https://*.corp.google.com", "https://*.corp.google.com:*"], "method": ["GET"]}]}, "location": "us-central1", "resource_url": ""}, "ancestors": ["projects/360989076580"], "update_time": "2022-02-07T20:35:50.128Z", "org_policy": []}'
    ],
    [
        '{"name": "//storage.googleapis.com/lakjsdklasjd", "asset_type": "storage.googleapis.com/Bucket", "resource": {"version": "v1", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/storage/v1/rest", "discovery_name": "Bucket", "parent": "//cloudresourcemanager.googleapis.com/projects/360989076580", "data": {"lifecycle": {"rule": []}, "storageClass": "NEARLINE", "id": "lakjsdklasjd", "etag": "CAE=", "retentionPolicy": {}, "acl": [], "billing": {}, "defaultObjectAcl": [], "metageneration": 1.0, "owner": {}, "labels": {"important": "no", "team": "cloud"}, "satisfiesPZS": false, "encryption": {}, "name": "lakjsdklasjd", "locationType": "region", "logging": {}, "kind": "storage#bucket", "location": "EUROPE-WEST3", "projectNumber": 360989076580.0, "website": {}, "updated": "2022-01-19T09:33:25.853Z", "versioning": {}, "selfLink": "https://www.googleapis.com/storage/v1/b/lakjsdklasjd", "cors": [], "timeCreated": "2022-01-19T09:33:25.853Z", "iamConfiguration": {"uniformBucketLevelAccess": {"enabled": true, "lockedTime": "2022-04-19T09:33:25.853Z"}, "bucketPolicyOnly": {"enabled": true, "lockedTime": "2022-04-19T09:33:25.853Z"}, "publicAccessPrevention": "inherited"}, "autoclass": {}}, "location": "europe-west3", "resource_url": ""}, "ancestors": ["projects/360989076580"], "update_time": "2022-01-19T09:33:25.853Z", "org_policy": []}'
    ],
    [
        '{"name": "//storage.googleapis.com/us.artifacts.backup-255820.appspot.com", "asset_type": "storage.googleapis.com/Bucket", "resource": {"version": "v1", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/storage/v1/rest", "discovery_name": "Bucket", "parent": "//cloudresourcemanager.googleapis.com/projects/360989076580", "data": {"labels": {}, "acl": [], "versioning": {}, "id": "us.artifacts.backup-255820.appspot.com", "retentionPolicy": {}, "iamConfiguration": {"publicAccessPrevention": "inherited", "bucketPolicyOnly": {"enabled": false}, "uniformBucketLevelAccess": {"enabled": false}}, "autoclass": {}, "owner": {}, "location": "US", "name": "us.artifacts.backup-255820.appspot.com", "locationType": "multi-region", "metageneration": 1.0, "timeCreated": "2022-02-07T20:36:32.368Z", "kind": "storage#bucket", "etag": "CAE=", "website": {}, "projectNumber": 360989076580.0, "logging": {}, "defaultObjectAcl": [], "updated": "2022-02-07T20:36:32.368Z", "storageClass": "STANDARD", "selfLink": "https://www.googleapis.com/storage/v1/b/us.artifacts.backup-255820.appspot.com", "billing": {}, "encryption": {}, "lifecycle": {"rule": []}, "cors": []}, "location": "us", "resource_url": ""}, "ancestors": ["projects/360989076580"], "update_time": "2022-02-07T20:36:32.368Z", "org_policy": []}'
    ],
]


def test_parse_gcp():
    section = parse_gcp_gcs(SECTION_TABLE)
    n_rows = sum(len(i.rows) for i in section.values())
    # first row contains general section information and no metrics
    assert n_rows == len(SECTION_TABLE)


@pytest.fixture(name="asset_section")
def fixture_asset_section():
    return gcp.parse_assets(ASSET_TABLE)


@pytest.fixture(name="buckets")
def fixture_buckets(asset_section):
    return list(discover(section_gcp_service_gcs=None, section_gcp_assets=asset_section))


def test_no_asset_section_yields_no_service():
    assert len(list(discover(section_gcp_service_gcs=None, section_gcp_assets=None))) == 0


def test_discover_all_buckets(buckets: Sequence[Service]):
    assert {b.item for b in buckets} == {
        "backup-home-ml-free",
        "lakjsdklasjd",
        "gcf-sources-360989076580-us-central1",
        "us.artifacts.backup-255820.appspot.com",
    }


def test_discover_project_labels(buckets: Sequence[Service]):
    for bucket in buckets:
        assert ServiceLabel("gcp/projectId", "backup-255820") in bucket.labels


def test_discover_bucket_labels(buckets: Sequence[Service]):
    labels = buckets[0].labels
    assert set(labels) == {
        ServiceLabel("gcp/labels/tag", "freebackup"),
        ServiceLabel("gcp/location", "US-CENTRAL1"),
        ServiceLabel("gcp/bucket/storageClass", "STANDARD"),
        ServiceLabel("gcp/bucket/locationType", "region"),
        ServiceLabel("gcp/projectId", "backup-255820"),
    }


@pytest.fixture(name="gcs_section")
def fixture_section():
    return parse_gcp_gcs(SECTION_TABLE)


@dataclass(frozen=True)
class Plugin:
    metrics: Sequence[str]
    function: Callable


PLUGINS = [
    Plugin(function=check_gcp_gcs_requests, metrics=["requests"]),
    Plugin(function=check_gcp_gcs_network, metrics=["net_data_recv", "net_data_sent"]),
    Plugin(function=check_gcp_gcs_object, metrics=["aws_bucket_size", "aws_num_objects"]),
]
ITEM = "backup-home-ml-free"


@pytest.fixture(params=PLUGINS, name="checkplugin")
def fixture_checkplugin(request):
    return request.param


@pytest.fixture(name="results")
def fixture_results(checkplugin, gcs_section):
    params = {k: None for k in checkplugin.metrics}
    results = list(
        checkplugin.function(
            item=ITEM, params=params, section_gcp_service_gcs=gcs_section, section_gcp_assets=None
        )
    )
    return results, checkplugin


def test_no_gcs_section_yields_no_metric_data(checkplugin):
    params = {k: None for k in checkplugin.metrics}
    results = list(
        checkplugin.function(
            item=ITEM, params=params, section_gcp_service_gcs=None, section_gcp_assets=None
        )
    )
    assert len(results) == 0


def test_yield_metrics_as_specified(results):
    results, checkplugin = results
    res = {r.name: r for r in results if isinstance(r, Metric)}
    assert len(res) == len(checkplugin.metrics)
    assert set(res.keys()) == set(checkplugin.metrics)


def test_yield_results_as_specified(results):
    results, checkplugin = results
    res = [r for r in results if isinstance(r, Result)]
    assert len(res) == len(checkplugin.metrics)
    for r in res:
        assert r.state == State.OK


class TestDefaultMetricValues:
    # requests does not contain example data
    def test_zero_default_if_metric_does_not_exist(self, gcs_section):
        params = {k: None for k in ["requests"]}
        results = (
            el
            for el in check_gcp_gcs_requests(
                item=ITEM,
                params=params,
                section_gcp_service_gcs=gcs_section,
                section_gcp_assets=None,
            )
            if isinstance(el, Metric)
        )
        for result in results:
            assert result.value == 0.0

    # objects does contain example data
    def test_non_zero_if_metric_exist(self, gcs_section):
        params = {k: None for k in ["aws_bucket_size", "aws_num_objects"]}
        results = (
            el
            for el in check_gcp_gcs_object(
                item=ITEM,
                params=params,
                section_gcp_service_gcs=gcs_section,
                section_gcp_assets=None,
            )
            if isinstance(el, Metric)
        )
        for result in results:
            assert result.value != 0.0


class TestConfiguredNotificationLevels:
    # In the example sections we do not have data for all metrics. To be able to test all check plugins
    # use 0, the default value, to check notification levels.
    def test_warn_levels(self, checkplugin, gcs_section):
        params = {k: (0, None) for k in checkplugin.metrics}
        results = list(
            checkplugin.function(
                item=ITEM, params=params, section_gcp_service_gcs=gcs_section, section_gcp_assets=[]
            )
        )
        results = [r for r in results if isinstance(r, Result)]
        for r in results:
            assert r.state == State.WARN

    def test_crit_levels(self, checkplugin, gcs_section):
        params = {k: (None, 0) for k in checkplugin.metrics}
        results = list(
            checkplugin.function(
                item=ITEM, params=params, section_gcp_service_gcs=gcs_section, section_gcp_assets=[]
            )
        )
        results = [r for r in results if isinstance(r, Result)]
        for r in results:
            assert r.state == State.CRIT
