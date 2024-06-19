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
from cmk.plugins.gcp.agent_based.gcp_gce_storage import (
    check_storage,
    check_summary,
    discover,
    parse,
)
from cmk.plugins.gcp.lib import gcp
from cmk.plugins.gcp.special_agents.agent_gcp import GCE_STORAGE

from .gcp_test_util import DiscoverTester, generate_stringtable, Plugin

ASSET_TABLE = [
    [f'{{"project":"backup-255820", "config":["{GCE_STORAGE.name}"]}}'],
    [
        '{"name": "//compute.googleapis.com/projects/checkmk-check-development/zones/us-central1-a/disks/with-labels", "asset_type": "compute.googleapis.com/Disk", "resource": {"version": "v1", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/compute/v1/rest", "discovery_name": "Disk", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {"type": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/diskTypes/pd-balanced", "status": "READY", "physicalBlockSizeBytes": "4096", "sizeGb": "10", "selfLink": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/disks/with-labels", "labels": {"amon": "amarth", "judas": "priest"}, "labelFingerprint": "qig8Gf7QLPc=", "zone": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a", "id": "6876419180096736884", "creationTimestamp": "2022-08-11T05:05:47.456-07:00", "name": "with-labels"}, "location": "us-central1-a", "resource_url": ""}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-08-11T12:05:47.734688Z", "org_policy": []}'
    ],
    [
        '{"name": "//compute.googleapis.com/projects/checkmk-check-development/zones/us-central1-a/disks/allin", "asset_type": "compute.googleapis.com/Disk", "resource": {"version": "v1", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/compute/v1/rest", "discovery_name": "Disk", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {"lastAttachTimestamp": "2022-08-03T05:12:23.112-07:00", "id": "1866579905098537810", "users": ["https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/instances/instance-2", "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/instances/instance-1"], "status": "READY", "physicalBlockSizeBytes": "4096", "labelFingerprint": "42WmSpB8rSM=", "type": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/diskTypes/pd-balanced", "creationTimestamp": "2022-08-03T05:10:37.177-07:00", "name": "allin", "sizeGb": "10", "zone": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a", "resourcePolicies": ["https://www.googleapis.com/compute/v1/projects/checkmk-check-development/regions/us-central1/resourcePolicies/default-schedule-1"], "selfLink": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/disks/allin"}, "location": "us-central1-a", "resource_url": ""}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-08-03T12:12:23.242728Z", "org_policy": []}'
    ],
    [
        '{"name": "//compute.googleapis.com/projects/checkmk-check-development/zones/us-central1-a/disks/disk-1", "asset_type": "compute.googleapis.com/Disk", "resource": {"version": "v1", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/compute/v1/rest", "discovery_name": "Disk", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {"zone": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a", "selfLink": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/disks/disk-1", "physicalBlockSizeBytes": "4096", "status": "READY", "resourcePolicies": ["https://www.googleapis.com/compute/v1/projects/checkmk-check-development/regions/us-central1/resourcePolicies/default-schedule-1"], "labelFingerprint": "araLniwO3D4=", "labels": {"war": "hammer", "iron": "maiden"}, "name": "disk-1", "creationTimestamp": "2022-05-19T07:14:14.952-07:00", "lastDetachTimestamp": "2022-07-10T23:55:49.501-07:00", "sizeGb": "100", "lastAttachTimestamp": "2022-08-03T05:12:52.196-07:00", "type": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/diskTypes/pd-balanced", "id": "6700634951876603481", "users": ["https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/instances/instance-3"]}, "location": "us-central1-a", "resource_url": ""}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-08-03T12:12:52.293556Z", "org_policy": []}'
    ],
    [
        '{"name": "//compute.googleapis.com/projects/checkmk-check-development/zones/us-central1-a/disks/instance-1", "asset_type": "compute.googleapis.com/Disk", "resource": {"version": "v1", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/compute/v1/rest", "discovery_name": "Disk", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {"sourceImageId": "4932115930768171344", "licenseCodes": ["3853522013536123851"], "physicalBlockSizeBytes": "4096", "selfLink": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/disks/instance-1", "users": ["https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/instances/instance-1"], "name": "instance-1", "status": "READY", "licenses": ["https://www.googleapis.com/compute/v1/projects/debian-cloud/global/licenses/debian-11-bullseye"], "lastAttachTimestamp": "2022-08-03T05:11:47.398-07:00", "creationTimestamp": "2022-08-03T05:11:47.397-07:00", "id": "3285748721601992941", "guestOsFeatures": [{"type": "UEFI_COMPATIBLE"}, {"type": "VIRTIO_SCSI_MULTIQUEUE"}, {"type": "GVNIC"}], "type": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/diskTypes/pd-balanced", "labelFingerprint": "42WmSpB8rSM=", "sourceImage": "https://www.googleapis.com/compute/v1/projects/debian-cloud/global/images/debian-11-bullseye-v20220719", "zone": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a", "sizeGb": "10"}, "location": "us-central1-a", "resource_url": ""}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-08-03T12:11:53.178098Z", "org_policy": []}'
    ],
    [
        '{"name": "//compute.googleapis.com/projects/checkmk-check-development/zones/us-central1-a/disks/instance-2", "asset_type": "compute.googleapis.com/Disk", "resource": {"version": "v1", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/compute/v1/rest", "discovery_name": "Disk", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {"physicalBlockSizeBytes": "4096", "labelFingerprint": "42WmSpB8rSM=", "creationTimestamp": "2022-08-03T05:12:23.111-07:00", "guestOsFeatures": [{"type": "UEFI_COMPATIBLE"}, {"type": "VIRTIO_SCSI_MULTIQUEUE"}, {"type": "GVNIC"}], "type": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/diskTypes/pd-balanced", "lastAttachTimestamp": "2022-08-03T05:12:23.111-07:00", "sizeGb": "10", "sourceImageId": "4932115930768171344", "id": "8156064970376206537", "licenseCodes": ["3853522013536123851"], "status": "READY", "sourceImage": "https://www.googleapis.com/compute/v1/projects/debian-cloud/global/images/debian-11-bullseye-v20220719", "licenses": ["https://www.googleapis.com/compute/v1/projects/debian-cloud/global/licenses/debian-11-bullseye"], "users": ["https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/instances/instance-2"], "zone": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a", "selfLink": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/disks/instance-2", "name": "instance-2"}, "location": "us-central1-a", "resource_url": ""}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-08-03T12:12:30.518037Z", "org_policy": []}'
    ],
    [
        '{"name": "//compute.googleapis.com/projects/checkmk-check-development/zones/us-central1-a/disks/instance-3", "asset_type": "compute.googleapis.com/Disk", "resource": {"version": "v1", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/compute/v1/rest", "discovery_name": "Disk", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {"labelFingerprint": "42WmSpB8rSM=", "lastAttachTimestamp": "2022-08-03T05:12:52.194-07:00", "name": "instance-3", "guestOsFeatures": [{"type": "UEFI_COMPATIBLE"}, {"type": "VIRTIO_SCSI_MULTIQUEUE"}, {"type": "GVNIC"}], "physicalBlockSizeBytes": "4096", "creationTimestamp": "2022-08-03T05:12:52.193-07:00", "licenseCodes": ["3853522013536123851"], "sourceImageId": "4932115930768171344", "id": "2753855350280542380", "sourceImage": "https://www.googleapis.com/compute/v1/projects/debian-cloud/global/images/debian-11-bullseye-v20220719", "licenses": ["https://www.googleapis.com/compute/v1/projects/debian-cloud/global/licenses/debian-11-bullseye"], "zone": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a", "type": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/diskTypes/pd-balanced", "users": ["https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/instances/instance-3"], "sizeGb": "10", "status": "READY", "selfLink": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/disks/instance-3"}, "location": "us-central1-a", "resource_url": ""}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-08-03T12:13:02.403059Z", "org_policy": []}'
    ],
]


class TestGCSDiscover(DiscoverTester):
    @property
    def _assets(self) -> StringTable:
        return ASSET_TABLE

    @property
    def expected_items(self) -> set[str]:
        return {"with-labels", "allin", "disk-1", "instance-1", "instance-2", "instance-3"}

    @property
    def expected_labels(self) -> set[ServiceLabel]:
        return {
            ServiceLabel("cmk/gcp/location", "us-central1-a"),
            ServiceLabel("cmk/gcp/labels/amon", "amarth"),
            ServiceLabel("cmk/gcp/labels/judas", "priest"),
        }

    def discover(self, assets: gcp.AssetSection | None) -> DiscoveryResult:
        yield from discover(section_gcp_service_gce_storage=None, section_gcp_assets=assets)


def test_discover_disk_labels_without_user_labels() -> None:
    asset_table = [
        [f'{{"project":"backup-255820", "config":["{GCE_STORAGE.name}"]}}'],
        [
            '{"name": "//compute.googleapis.com/projects/checkmk-check-development/zones/us-central1-a/disks/instance-3", "asset_type": "compute.googleapis.com/Disk", "resource": {"version": "v1", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/compute/v1/rest", "discovery_name": "Disk", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {"labelFingerprint": "42WmSpB8rSM=", "lastAttachTimestamp": "2022-08-03T05:12:52.194-07:00", "name": "instance-3", "guestOsFeatures": [{"type": "UEFI_COMPATIBLE"}, {"type": "VIRTIO_SCSI_MULTIQUEUE"}, {"type": "GVNIC"}], "physicalBlockSizeBytes": "4096", "creationTimestamp": "2022-08-03T05:12:52.193-07:00", "licenseCodes": ["3853522013536123851"], "sourceImageId": "4932115930768171344", "id": "2753855350280542380", "sourceImage": "https://www.googleapis.com/compute/v1/projects/debian-cloud/global/images/debian-11-bullseye-v20220719", "licenses": ["https://www.googleapis.com/compute/v1/projects/debian-cloud/global/licenses/debian-11-bullseye"], "zone": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a", "type": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/diskTypes/pd-balanced", "users": ["https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/instances/instance-3"], "sizeGb": "10", "status": "READY", "selfLink": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/disks/instance-3"}, "location": "us-central1-a", "resource_url": ""}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-08-03T12:13:02.403059Z", "org_policy": []}'
        ],
    ]
    asset_section = parse_assets(asset_table)
    disks = list(discover(section_gcp_service_gce_storage=None, section_gcp_assets=asset_section))
    labels = disks[0].labels
    assert set(labels) == {
        ServiceLabel("cmk/gcp/location", "us-central1-a"),
    }


PLUGINS = [
    pytest.param(
        Plugin(
            function=check_storage,
            metrics=[
                "disk_read_throughput",
                "disk_write_throughput",
                "disk_read_ios",
                "disk_write_ios",
            ],
            results=[
                Result(state=State.OK, summary="Read: 42.0 B/s"),
                Result(state=State.OK, summary="Write: 42.0 B/s"),
                Result(state=State.OK, summary="Read operations: 42.0"),
                Result(state=State.OK, summary="Write operations: 42.0"),
            ],
        ),
        id="storage",
    ),
]


def generate_results(plugin: Plugin) -> CheckResult:
    item = "item"
    asset_table = [
        [f'{{"project":"backup-255820", "config":["{GCE_STORAGE.name}"]}}'],
        [
            '{"name": "//compute.googleapis.com/projects/checkmk-check-development/zones/us-central1-a/disks/item", "asset_type": "compute.googleapis.com/Disk", "resource": {"version": "v1", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/compute/v1/rest", "discovery_name": "Disk", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {"type": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/diskTypes/pd-balanced", "status": "READY", "physicalBlockSizeBytes": "4096", "sizeGb": "10", "selfLink": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/disks/item", "labels": {"amon": "amarth", "judas": "priest"}, "labelFingerprint": "qig8Gf7QLPc=", "zone": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a", "id": "6876419180096736884", "creationTimestamp": "2022-08-11T05:05:47.456-07:00", "name": "item"}, "location": "us-central1-a", "resource_url": ""}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-08-11T12:05:47.734688Z", "org_policy": []}'
        ],
    ]
    section = parse(generate_stringtable(item, 42.0, GCE_STORAGE))
    yield from plugin.function(
        item=item,
        params={k: None for k in plugin.metrics},
        section_gcp_service_gce_storage=section,
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
    assert results == {Result(state=State.OK, summary="6 Disks", details="Found 6 disks")}
