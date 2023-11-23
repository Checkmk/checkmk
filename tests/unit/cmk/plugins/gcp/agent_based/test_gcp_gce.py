#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs
import pytest

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.gcp.agent_based.gcp_assets import parse_assets
from cmk.plugins.gcp.agent_based.gcp_gce import (
    check_disk_summary,
    check_network,
    check_summary,
    parse_gce_uptime,
)
from cmk.plugins.gcp.lib import gcp
from cmk.plugins.gcp.special_agents import agent_gcp
from cmk.plugins.lib import uptime
from cmk.plugins.lib.interfaces import CHECK_DEFAULT_PARAMETERS


def test_parse_piggy_back() -> None:
    uptime_section = parse_gce_uptime(
        [
            [
                '{"ts": {"metric": {"type": "compute.googleapis.com/instance/uptime_total", "labels": {}}, "resource": {"type": "gce_instance", "labels": {"project_id": "checkmk-check-development", "instance_id": "4916403162284897775"}}, "metric_kind": 1, "value_type": 2, "points": [{"interval": {"start_time": "2022-05-05T13:55:15.478132Z", "end_time": "2022-05-05T13:55:15.478132Z"}, "value": {"int64_value": "10"}}], "unit": ""}, "aggregation": {}}'
            ],
        ]
    )
    assert uptime_section == uptime.Section(uptime_sec=10, message=None)


# test if I call the network check correct
NETWORK_SECTION = [
    [
        '{"ts": {"metric": {"type": "compute.googleapis.com/instance/network/received_bytes_count", "labels": {}}, "resource": {"type": "gce_instance", "labels": {"project_id": "checkmk-check-development", "instance_id": "4916403162284897775"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-05-18T12:38:32.833429Z", "end_time": "2022-05-18T12:38:32.833429Z"}, "value": {"double_value": 385.4}}, {"interval": {"start_time": "2022-05-18T12:37:32.833429Z", "end_time": "2022-05-18T12:37:32.833429Z"}, "value": {"double_value": 894.0666666666667}}, {"interval": {"start_time": "2022-05-18T12:36:32.833429Z", "end_time": "2022-05-18T12:36:32.833429Z"}, "value": {"double_value": 717.3333333333334}}, {"interval": {"start_time": "2022-05-18T12:35:32.833429Z", "end_time": "2022-05-18T12:35:32.833429Z"}, "value": {"double_value": 280.25}}, {"interval": {"start_time": "2022-05-18T12:34:32.833429Z", "end_time": "2022-05-18T12:34:32.833429Z"}, "value": {"double_value": 144.31666666666666}}, {"interval": {"start_time": "2022-05-18T12:33:32.833429Z", "end_time": "2022-05-18T12:33:32.833429Z"}, "value": {"double_value": 40178.35}}, {"interval": {"start_time": "2022-05-18T12:32:32.833429Z", "end_time": "2022-05-18T12:32:32.833429Z"}, "value": {"double_value": 22187.466666666667}}, {"interval": {"start_time": "2022-05-18T12:31:32.833429Z", "end_time": "2022-05-18T12:31:32.833429Z"}, "value": {"double_value": 149.1}}, {"interval": {"start_time": "2022-05-18T12:30:32.833429Z", "end_time": "2022-05-18T12:30:32.833429Z"}, "value": {"double_value": 148.98333333333332}}, {"interval": {"start_time": "2022-05-18T12:29:32.833429Z", "end_time": "2022-05-18T12:29:32.833429Z"}, "value": {"double_value": 304.1}}, {"interval": {"start_time": "2022-05-18T12:28:32.833429Z", "end_time": "2022-05-18T12:28:32.833429Z"}, "value": {"double_value": 276.21666666666664}}, {"interval": {"start_time": "2022-05-18T12:27:32.833429Z", "end_time": "2022-05-18T12:27:32.833429Z"}, "value": {"double_value": 232.43333333333334}}, {"interval": {"start_time": "2022-05-18T12:26:32.833429Z", "end_time": "2022-05-18T12:26:32.833429Z"}, "value": {"double_value": 224.08333333333334}}, {"interval": {"start_time": "2022-05-18T12:25:32.833429Z", "end_time": "2022-05-18T12:25:32.833429Z"}, "value": {"double_value": 329.03333333333336}}, {"interval": {"start_time": "2022-05-18T12:24:32.833429Z", "end_time": "2022-05-18T12:24:32.833429Z"}, "value": {"double_value": 306.8833333333333}}, {"interval": {"start_time": "2022-05-18T12:23:32.833429Z", "end_time": "2022-05-18T12:23:32.833429Z"}, "value": {"double_value": 203.33333333333334}}, {"interval": {"start_time": "2022-05-18T12:22:32.833429Z", "end_time": "2022-05-18T12:22:32.833429Z"}, "value": {"double_value": 170.11666666666667}}], "unit": ""}, "aggregation": {}}'
    ],
    [
        '{"ts": {"metric": {"type": "compute.googleapis.com/instance/network/sent_bytes_count", "labels": {}}, "resource": {"type": "gce_instance", "labels": {"project_id": "checkmk-check-development", "instance_id": "4916403162284897775"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-05-18T12:39:32.833429Z", "end_time": "2022-05-18T12:39:32.833429Z"}, "value": {"double_value": 245.26666666666668}}, {"interval": {"start_time": "2022-05-18T12:38:32.833429Z", "end_time": "2022-05-18T12:38:32.833429Z"}, "value": {"double_value": 225.58333333333334}}, {"interval": {"start_time": "2022-05-18T12:37:32.833429Z", "end_time": "2022-05-18T12:37:32.833429Z"}, "value": {"double_value": 111.25}}, {"interval": {"start_time": "2022-05-18T12:36:32.833429Z", "end_time": "2022-05-18T12:36:32.833429Z"}, "value": {"double_value": 59.63333333333333}}, {"interval": {"start_time": "2022-05-18T12:35:32.833429Z", "end_time": "2022-05-18T12:35:32.833429Z"}, "value": {"double_value": 58.333333333333336}}, {"interval": {"start_time": "2022-05-18T12:34:32.833429Z", "end_time": "2022-05-18T12:34:32.833429Z"}, "value": {"double_value": 58.7}}, {"interval": {"start_time": "2022-05-18T12:33:32.833429Z", "end_time": "2022-05-18T12:33:32.833429Z"}, "value": {"double_value": 232.53333333333333}}, {"interval": {"start_time": "2022-05-18T12:32:32.833429Z", "end_time": "2022-05-18T12:32:32.833429Z"}, "value": {"double_value": 137.93333333333334}}, {"interval": {"start_time": "2022-05-18T12:31:32.833429Z", "end_time": "2022-05-18T12:31:32.833429Z"}, "value": {"double_value": 61.25}}, {"interval": {"start_time": "2022-05-18T12:30:32.833429Z", "end_time": "2022-05-18T12:30:32.833429Z"}, "value": {"double_value": 59.85}}, {"interval": {"start_time": "2022-05-18T12:29:32.833429Z", "end_time": "2022-05-18T12:29:32.833429Z"}, "value": {"double_value": 56.53333333333333}}, {"interval": {"start_time": "2022-05-18T12:28:32.833429Z", "end_time": "2022-05-18T12:28:32.833429Z"}, "value": {"double_value": 36.43333333333333}}, {"interval": {"start_time": "2022-05-18T12:27:32.833429Z", "end_time": "2022-05-18T12:27:32.833429Z"}, "value": {"double_value": 30.366666666666667}}, {"interval": {"start_time": "2022-05-18T12:26:32.833429Z", "end_time": "2022-05-18T12:26:32.833429Z"}, "value": {"double_value": 67.53333333333333}}, {"interval":{"start_time": "2022-05-18T12:25:32.833429Z", "end_time": "2022-05-18T12:25:32.833429Z"}, "value": {"double_value": 107.86666666666666}}, {"interval": {"start_time": "2022-05-18T12:24:32.833429Z", "end_time": "2022-05-18T12:24:32.833429Z"}, "value": {"double_value": 123.6}}, {"interval": {"start_time": "2022-05-18T12:23:32.833429Z", "end_time": "2022-05-18T12:23:32.833429Z"}, "value": {"double_value": 111.33333333333333}}, {"interval": {"start_time": "2022-05-18T12:22:32.833429Z", "end_time": "2022-05-18T12:22:32.833429Z"}, "value": {"double_value": 60.45}}], "unit": ""}, "aggregation": {}}'
    ],
]


@pytest.mark.usefixtures("initialised_item_state")
def test_network_check() -> None:
    section = gcp.parse_piggyback(NETWORK_SECTION)
    params = CHECK_DEFAULT_PARAMETERS
    item = "nic0"
    results = list(check_network(item, params, section))
    assert results == [
        Result(state=State.OK, summary="[0]"),
        Result(state=State.OK, summary="(up)", details="Operational state: up"),
        Result(state=State.OK, summary="Speed: unknown"),
        Result(state=State.OK, summary="In: 385 B/s"),
        Metric("in", 385.4, boundaries=(0.0, None)),
        Result(state=State.OK, summary="Out: 245 B/s"),
        Metric("out", 245.26666666666668, boundaries=(0.0, None)),
    ]


DISK_SECTION = [
    [
        '{"ts": {"metric": {"type": "compute.googleapis.com/instance/disk/read_bytes_count", "labels": {}}, "resource": {"type": "gce_instance", "labels": {"instance_id": "1807848413475835096", "project_id": "checkmk-check-development"}}, "metric_kind": 2, "value_type": 2, "points": [{"interval": {"start_time": "2022-05-23T12:57:11.921195Z", "end_time": "2022-05-23T12:58:11.921195Z"}, "value": {"int64_value": "2"}}], "unit": ""}, "aggregation": {}}'
    ],
    [
        '{"ts": {"metric": {"type": "compute.googleapis.com/instance/disk/read_ops_count", "labels": {}}, "resource": {"type": "gce_instance", "labels": {"project_id": "checkmk-check-development", "instance_id": "1807848413475835096"}}, "metric_kind": 2, "value_type": 2, "points": [{"interval": {"start_time": "2022-05-23T12:57:11.921195Z", "end_time": "2022-05-23T12:58:11.921195Z"}, "value": {"int64_value": "4"}}], "unit": ""}, "aggregation": {}}'
    ],
    [
        '{"ts": {"metric": {"type": "compute.googleapis.com/instance/disk/write_bytes_count", "labels": {}}, "resource": {"type": "gce_instance", "labels": {"instance_id": "1807848413475835096", "project_id": "checkmk-check-development"}}, "metric_kind": 2, "value_type": 2, "points": [{"interval": {"start_time": "2022-05-23T12:57:11.921195Z", "end_time": "2022-05-23T12:58:11.921195Z"}, "value": {"int64_value": "8"}}], "unit": ""}, "aggregation": {}}'
    ],
    [
        '{"ts": {"metric": {"type": "compute.googleapis.com/instance/disk/write_ops_count", "labels": {}}, "resource": {"type": "gce_instance", "labels": {"project_id": "checkmk-check-development", "instance_id": "1807848413475835096"}}, "metric_kind": 2, "value_type": 2, "points": [{"interval": {"start_time": "2022-05-23T12:57:11.921195Z", "end_time": "2022-05-23T12:58:11.921195Z"}, "value": {"int64_value": "16"}}], "unit": ""}, "aggregation": {}}'
    ],
]


def test_disk_summary_check() -> None:
    section = gcp.parse_piggyback(DISK_SECTION)
    params = {
        "disk_read_throughput": None,
        "disk_write_throughput": None,
        "disk_read_ios": None,
        "disk_write_ios": None,
    }
    results = list(check_disk_summary(params, section))
    assert results == [
        Result(state=State.OK, summary="Read: 2.00 B/s"),
        Metric("disk_read_throughput", 2.0),
        Result(state=State.OK, summary="Write: 8.00 B/s"),
        Metric("disk_write_throughput", 8.0),
        Result(state=State.OK, summary="Read operations: 4.0"),
        Metric("disk_read_ios", 4.0),
        Result(state=State.OK, summary="Write operations: 16.0"),
        Metric("disk_write_ios", 16.0),
    ]


ASSET_TABLE = [
    [f'{{"project":"backup-255820", "config":["{agent_gcp.GCE.name}"]}}'],
    [
        '{"name": "//compute.googleapis.com/projects/checkmk-check-development/zones/us-central1-a/instances/instance-1", "asset_type": "compute.googleapis.com/Instance", "resource": {"version": "v1", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/compute/v1/rest", "discovery_name": "Instance", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {"deletionProtection": false, "displayDevice": {"enableDisplay": false}, "lastStartTimestamp": "2022-03-28T02:37:10.106-07:00", "creationTimestamp": "2022-03-18T06:37:06.655-07:00", "id": "4916403162284897775", "name": "instance-1", "lastStopTimestamp": "2022-04-05T01:23:00.444-07:00", "machineType": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/machineTypes/f1-micro", "selfLink": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/instances/instance-1", "tags": {"fingerprint": "42WmSpB8rSM="}, "fingerprint": "im05qPmW++Q=", "status": "TERMINATED", "shieldedInstanceIntegrityPolicy": {"updateAutoLearnPolicy": true}, "shieldedInstanceConfig": {"enableIntegrityMonitoring": true, "enableSecureBoot": false, "enableVtpm": true}, "startRestricted": false, "description": "", "confidentialInstanceConfig": {"enableConfidentialCompute": false}, "zone": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a", "canIpForward": false, "disks": [{"type": "PERSISTENT", "boot": true, "licenses": ["https://www.googleapis.com/compute/v1/projects/debian-cloud/global/licenses/debian-10-buster"], "mode": "READ_WRITE", "index": 0.0, "source": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/zones/us-central1-a/disks/instance-1", "deviceName": "instance-1", "diskSizeGb": "10", "guestOsFeatures": [{"type": "UEFI_COMPATIBLE"}, {"type": "VIRTIO_SCSI_MULTIQUEUE"}], "interface": "SCSI", "autoDelete": true}], "cpuPlatform": "Unknown CPU Platform", "labelFingerprint": "6Ok5Ta5mo84=", "allocationAffinity": {"consumeAllocationType": "ANY_ALLOCATION"}, "networkInterfaces": [{"network": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/global/networks/default", "name": "nic0", "subnetwork": "https://www.googleapis.com/compute/v1/projects/checkmk-check-development/regions/us-central1/subnetworks/default", "networkIP": "10.128.0.2", "stackType": "IPV4_ONLY", "accessConfigs": [{"name": "External NAT", "networkTier": "PREMIUM", "type": "ONE_TO_ONE_NAT"}], "fingerprint": "h7uoBU+ZS74="}], "serviceAccounts": [{"email": "1074106860578-compute@developer.gserviceaccount.com", "scopes": ["https://www.googleapis.com/auth/devstorage.read_only", "https://www.googleapis.com/auth/logging.write", "https://www.googleapis.com/auth/monitoring.write", "https://www.googleapis.com/auth/servicecontrol", "https://www.googleapis.com/auth/service.management.readonly", "https://www.googleapis.com/auth/trace.append"]}], "scheduling": {"preemptible": false, "automaticRestart": true, "onHostMaintenance": "MIGRATE"}, "labels": {"t": "tt"}}, "location": "us-central1-a", "resource_url": ""}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-04-05T08:23:00.662291Z", "org_policy": []}'
    ],
]


def test_check_summary() -> None:
    assets = parse_assets(ASSET_TABLE)
    results = set(check_summary(section=assets))
    assert results == {Result(state=State.OK, summary="1 VM", details="Found 1 VM")}
