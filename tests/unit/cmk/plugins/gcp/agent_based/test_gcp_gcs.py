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
from cmk.plugins.gcp.agent_based.gcp_gcs import (
    check_gcp_gcs_network,
    check_gcp_gcs_object,
    check_gcp_gcs_requests,
    check_summary,
    discover,
    parse_gcp_gcs,
)
from cmk.plugins.gcp.lib import gcp
from cmk.plugins.gcp.special_agents.agent_gcp import GCS

from .gcp_test_util import DiscoverTester, generate_stringtable, Plugin

ASSET_TABLE = [
    [f'{{"project":"backup-255820", "config":["{GCS.name}"]}}'],
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


class TestGCSDiscover(DiscoverTester):
    @property
    def _assets(self) -> StringTable:
        return ASSET_TABLE

    @property
    def expected_items(self) -> set[str]:
        return {
            "backup-home-ml-free",
            "lakjsdklasjd",
            "gcf-sources-360989076580-us-central1",
            "us.artifacts.backup-255820.appspot.com",
        }

    @property
    def expected_labels(self) -> set[ServiceLabel]:
        return {
            ServiceLabel("cmk/gcp/labels/tag", "freebackup"),
            ServiceLabel("cmk/gcp/location", "US-CENTRAL1"),
            ServiceLabel("cmk/gcp/bucket/storageClass", "STANDARD"),
            ServiceLabel("cmk/gcp/bucket/locationType", "region"),
        }

    def discover(self, assets: gcp.AssetSection | None) -> DiscoveryResult:
        yield from discover(section_gcp_service_gcs=None, section_gcp_assets=assets)


def test_discover_bucket_labels_without_user_labels() -> None:
    asset_table = [
        ['{"project":"backup-255820", "config":["gcs"]}'],
        [
            '{"name": "//storage.googleapis.com/backup-home-ml-free", "asset_type": "storage.googleapis.com/Bucket", "resource": {"version": "v1", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/storage/v1/rest", "discovery_name": "Bucket", "parent": "//cloudresourcemanager.googleapis.com/projects/360989076580", "data": {"name": "backup-home-ml-free", "id": "backup-home-ml-free", "labels": {}, "projectNumber": 360989076580.0, "timeCreated": "2019-11-03T13:48:57.905Z", "lifecycle": {"rule": []}, "metageneration": 1.0, "cors": [], "storageClass": "STANDARD", "etag": "CAE=", "kind": "storage#bucket", "billing": {}, "versioning": {}, "iamConfiguration": {"uniformBucketLevelAccess": {"enabled": false}, "bucketPolicyOnly": {"enabled": false}}, "owner": {}, "encryption": {}, "updated": "2019-11-03T13:48:57.905Z", "locationType": "region", "logging": {}, "acl": [], "retentionPolicy": {}, "defaultObjectAcl": [], "location": "US-CENTRAL1", "selfLink": "https://www.googleapis.com/storage/v1/b/backup-home-ml-free", "website": {}, "autoclass": {}}, "location": "us-central1", "resource_url": ""}, "ancestors": ["projects/360989076580"], "update_time": "2021-09-20T20:35:59.747Z", "org_policy": []}'
        ],
    ]
    asset_section = parse_assets(asset_table)
    buckets = list(discover(section_gcp_service_gcs=None, section_gcp_assets=asset_section))
    labels = buckets[0].labels
    assert set(labels) == {
        ServiceLabel("cmk/gcp/location", "US-CENTRAL1"),
        ServiceLabel("cmk/gcp/bucket/storageClass", "STANDARD"),
        ServiceLabel("cmk/gcp/bucket/locationType", "region"),
    }


PLUGINS = [
    pytest.param(
        Plugin(
            function=check_gcp_gcs_requests,
            metrics=["requests"],
            results=[Result(state=State.OK, summary="Requests: 42.0")],
        ),
        id="requetss",
    ),
    pytest.param(
        Plugin(
            function=check_gcp_gcs_network,
            metrics=["net_data_recv", "net_data_sent"],
            results=[
                Result(state=State.OK, summary="In: 336 Bit/s"),
                Result(state=State.OK, summary="Out: 336 Bit/s"),
            ],
        ),
        id="network",
    ),
    pytest.param(
        Plugin(
            function=check_gcp_gcs_object,
            metrics=["aws_bucket_size", "aws_num_objects"],
            results=[
                Result(state=State.OK, summary="Bucket size: 42 B"),
                Result(state=State.OK, summary="Objects: 42.0"),
            ],
        ),
        id="objects",
    ),
]


def generate_results(plugin: Plugin) -> CheckResult:
    item = "item"
    asset_table = [
        [f'{{"project":"backup-255820", "config":["{GCS.name}"]}}'],
        [
            f'{{"name": "//storage.googleapis.com/backup-home-ml-free", "asset_type": "storage.googleapis.com/Bucket", "resource": {{"version": "v1", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/storage/v1/rest", "discovery_name": "Bucket", "parent": "//cloudresourcemanager.googleapis.com/projects/360989076580", "data": {{"name": "backup-home-ml-free", "id": "{item}", "labels": {{"tag": "freebackup"}}, "projectNumber": 360989076580.0, "timeCreated": "2019-11-03T13:48:57.905Z", "lifecycle": {{"rule": []}}, "metageneration": 1.0, "cors": [], "storageClass": "STANDARD", "etag": "CAE=", "kind": "storage#bucket", "billing": {{}}, "versioning": {{}}, "iamConfiguration": {{"uniformBucketLevelAccess": {{"enabled": false}}, "bucketPolicyOnly": {{"enabled": false}}}}, "owner": {{}}, "encryption": {{}}, "updated": "2019-11-03T13:48:57.905Z", "locationType": "region", "logging": {{}}, "acl": [], "retentionPolicy": {{}}, "defaultObjectAcl": [], "location": "US-CENTRAL1", "selfLink": "https://www.googleapis.com/storage/v1/b/backup-home-ml-free", "website": {{}}, "autoclass": {{}}}}, "location": "us-central1", "resource_url": ""}}, "ancestors": ["projects/360989076580"], "update_time": "2021-09-20T20:35:59.747Z", "org_policy": []}}'
        ],
    ]
    section = parse_gcp_gcs(generate_stringtable(item, 42.0, GCS))
    yield from plugin.function(
        item=item,
        params={k: None for k in plugin.metrics},
        section_gcp_service_gcs=section,
        section_gcp_assets=parse_assets(asset_table),
    )


@pytest.mark.parametrize("plugin", PLUGINS)
def test_yield_results_as_specified(plugin: Plugin) -> None:
    results = {r for r in generate_results(plugin) if isinstance(r, Result)}
    assert results == set(plugin.results)


@pytest.mark.parametrize("plugin", PLUGINS)
def test_yield_metrics_as_specified(plugin: Plugin) -> None:
    results = {r.name for r in generate_results(plugin) if isinstance(r, Metric)}
    assert results == plugin.expected_metrics()


def test_check_summary() -> None:
    assets = parse_assets(ASSET_TABLE)
    results = set(check_summary(section=assets))
    assert results == {Result(state=State.OK, summary="4 Buckets", details="Found 4 buckets")}
