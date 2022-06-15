#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
import json
from typing import Any, Iterable, Optional, Sequence

import pytest
from google.cloud import asset_v1, monitoring_v3
from google.cloud.monitoring_v3 import Aggregation
from google.cloud.monitoring_v3.types import TimeSeries

# Those are enum classes defined in the Aggregation class. Not nice but works
Aligner = Aggregation.Aligner
Reducer = Aggregation.Reducer

from cmk.special_agents import agent_gcp

METRIC_TYPE = "compute.googleapis.com/instance/uptime"
METRIC_LABELS = {"instance_name": "instance-1"}
METRIC_LABELS2 = {"instance_name": "instance-2"}

RESOURCE_TYPE = "gce_instance"
RESOURCE_LABELS = {
    "project_id": "my-project",
    "zone": "us-east1-a",
    "instance_id": "1234567890123456789",
    "id": "a",
}
RESOURCE_LABELS2 = {
    "project_id": "my-project",
    "zone": "us-east1-b",
    "instance_id": "9876543210987654321",
    "id": "b",
}

METRIC_KIND = "DELTA"
VALUE_TYPE = "DOUBLE"

TS0 = datetime.datetime(2016, 4, 6, 22, 5, 0, 42)
TS1 = datetime.datetime(2016, 4, 6, 22, 5, 1, 42)
TS2 = datetime.datetime(2016, 4, 6, 22, 5, 2, 42)


class FakeMonitoringClient:
    def __init__(self, timeseries: Optional[Iterable[str]] = None) -> None:
        self._timeseries = timeseries

    def list_time_series(self, request: Any) -> Iterable[TimeSeries]:
        if self._timeseries is None:
            yield from self._fixed_list_time_series()
        else:
            for ts in self._timeseries:
                yield agent_gcp.Result.deserialize(ts).ts

    def _fixed_list_time_series(self) -> Iterable[TimeSeries]:
        def _make_interval(end_time, start_time):
            interval = monitoring_v3.TimeInterval(end_time=end_time, start_time=start_time)
            return interval

        INTERVAL1 = _make_interval(TS1, TS0)
        INTERVAL2 = _make_interval(TS2, TS1)

        VALUE1 = 60  # seconds
        VALUE2 = 42  # seconds

        # Currently cannot create from a list of dict for repeated fields due to
        # https://github.com/googleapis/proto-plus-python/issues/135
        POINT1 = monitoring_v3.Point({"interval": INTERVAL2, "value": {"double_value": VALUE1}})
        POINT2 = monitoring_v3.Point({"interval": INTERVAL1, "value": {"double_value": VALUE1}})
        POINT3 = monitoring_v3.Point({"interval": INTERVAL2, "value": {"double_value": VALUE2}})
        POINT4 = monitoring_v3.Point({"interval": INTERVAL1, "value": {"double_value": VALUE2}})
        SERIES1 = monitoring_v3.TimeSeries(
            {
                "metric": {"type": METRIC_TYPE, "labels": METRIC_LABELS},
                "resource": {"type": RESOURCE_TYPE, "labels": RESOURCE_LABELS},
                "metric_kind": METRIC_KIND,
                "value_type": VALUE_TYPE,
                "points": [POINT1, POINT2],
            }
        )
        SERIES2 = monitoring_v3.TimeSeries(
            {
                "metric": {"type": METRIC_TYPE, "labels": METRIC_LABELS2},
                "resource": {"type": RESOURCE_TYPE, "labels": RESOURCE_LABELS2},
                "metric_kind": METRIC_KIND,
                "value_type": VALUE_TYPE,
                "points": [POINT3, POINT4],
            }
        )
        yield SERIES1
        yield SERIES2

    def __call__(self) -> "FakeMonitoringClient":
        return self


class FakeAssetClient:
    def __init__(self, assets: Optional[Iterable[str]] = None) -> None:
        if assets is None:
            self._assets: Iterable[str] = [
                '{"name": "//compute.googleapis.com/projects/tribe29-check-development/zones/us-central1-a/instances/instance-1", "asset_type": "compute.googleapis.com/Instance", "resource": {"version": "v1", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/compute/v1/rest", "discovery_name": "Instance", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {}, "location": "us-central1-a", "resource_url": ""}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-04-05T08:23:00.662291Z", "org_policy": []}',
                '{"name": "//compute.googleapis.com/projects/tribe29-check-development/zones/us-central1-a/instances/instance-1", "asset_type": "foo", "resource": {"version": "v1", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/compute/v1/rest", "discovery_name": "Instance", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {"id":"a", "labels": {"judas": "priest", "iron": "maiden", "van":"halen"}}, "location": "us-central1-a", "resource_url": ""}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-04-05T08:23:00.662291Z", "org_policy": []}',
                '{"name": "//compute.googleapis.com/projects/tribe29-check-development/zones/us-central1-a/instances/instance-1", "asset_type": "foo", "resource": {"version": "v1", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/compute/v1/rest", "discovery_name": "Instance", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {"id":"b", "labels": {"judas": "priest", "iron": "maiden", "van":"halen"}}, "location": "us-central1-a", "resource_url": ""}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-04-05T08:23:00.662291Z", "org_policy": []}',
            ]
        else:
            self._assets = assets

    def list_assets(self, request: Any) -> Iterable[asset_v1.Asset]:
        for a in self._assets:
            yield agent_gcp.Asset.deserialize(a).asset

    def __call__(self) -> "FakeAssetClient":
        return self


class FakeClient:
    def __init__(
        self, project: str, monitoring_client: FakeMonitoringClient, asset_client: FakeAssetClient
    ):
        self.project = project
        self.monitoring_client = monitoring_client
        self.asset_client = asset_client

    def list_time_series(self, request: Any) -> Iterable[TimeSeries]:
        return self.monitoring_client.list_time_series(request)

    def list_assets(self, request: Any) -> Iterable[asset_v1.Asset]:
        return self.asset_client.list_assets(request)


def collector_factory(container: list[agent_gcp.Section]):
    def f(sections: Iterable[agent_gcp.Section]):
        container.extend(list(sections))

    return f


@pytest.fixture(name="agent_output")
def fixture_agent_output() -> Sequence[agent_gcp.Section]:
    client = FakeClient("test", FakeMonitoringClient(), FakeAssetClient())
    sections: list[agent_gcp.Section] = []
    collector = collector_factory(sections)
    agent_gcp.run(client, list(agent_gcp.SERVICES.values()), [], serializer=collector)
    return list(sections)


def test_output_contains_defined_metric_sections(agent_output: Sequence[agent_gcp.Section]) -> None:
    names = {s.name for s in agent_output}
    assert names.issuperset({s.name for s in agent_gcp.SERVICES.values()})


def test_output_contains_one_asset_section(agent_output: Sequence[agent_gcp.Section]) -> None:
    assert "asset" in {s.name for s in agent_output}
    asset_sections = list(s for s in agent_output if isinstance(s, agent_gcp.AssetSection))
    assert len(asset_sections) == 1
    assert asset_sections[0].project == "test"


def test_metric_serialization(agent_output: Sequence[agent_gcp.Section], capsys) -> None:
    result_section = next(s for s in agent_output if isinstance(s, agent_gcp.ResultSection))
    agent_gcp.gcp_serializer([result_section])
    captured = capsys.readouterr()
    lines = captured.out.rstrip().split("\n")
    assert lines[0] == f"<<<gcp_service_{result_section.name}:sep(0)>>>"
    for line in lines[1:]:
        agent_gcp.Result.deserialize(line)


def test_metric_retrieval() -> None:
    timeseries = [
        '{"metric": {"type": "compute.googleapis.com/instance/cpu/utilization", "labels": {}}, "resource": {"type": "gce_instance", "labels": {"project_id": "tribe29-check-development", "instance_id": "4916403162284897775"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-04-13T11:19:37.193318Z", "end_time": "2022-04-13T11:19:37.193318Z"}, "value": {"double_value": 0.0033734199011726433}}], "unit": ""}'
    ]
    client = FakeClient("test", FakeMonitoringClient(timeseries), FakeAssetClient())
    sections: list[agent_gcp.Section] = []
    collector = collector_factory(sections)
    agent_gcp.run(client, [agent_gcp.RUN], [], serializer=collector)
    result_section = next(
        s for s in sections if isinstance(s, agent_gcp.ResultSection) and s.name == "cloud_run"
    )
    results = list(result_section.results)
    assert len(results) == len(agent_gcp.RUN.metrics)


def test_asset_serialization(agent_output: Sequence[agent_gcp.Section], capsys) -> None:
    asset_section = next(s for s in agent_output if isinstance(s, agent_gcp.AssetSection))
    agent_gcp.gcp_serializer([asset_section])
    captured = capsys.readouterr()
    lines = captured.out.rstrip().split("\n")
    assert lines[0] == "<<<gcp_assets:sep(0)>>>"
    assert json.loads(lines[1]) == {"project": "test"}
    for line in lines[2:]:
        agent_gcp.Asset.deserialize(line)


@pytest.fixture(name="piggy_back_sections")
def piggy_back_sections_fixture():
    client = FakeClient("test", FakeMonitoringClient(), FakeAssetClient())
    sections: list[agent_gcp.Section] = []
    collector = collector_factory(sections)

    def test_labeler(asset: agent_gcp.Asset) -> agent_gcp.Labels:
        return {f"gcp/labels/{k}": v for k, v in asset.asset.resource.data["labels"].items()}

    piggy_back_section = agent_gcp.PiggyBackService(
        name="testing",
        asset_type="foo",
        asset_label="id",
        metric_label="id",
        name_label="id",
        labeler=test_labeler,
        services=[
            agent_gcp.Service(
                name="uptime",
                default_groupby="resource.instance_id",
                metrics=[
                    agent_gcp.Metric(
                        name="compute.googleapis.com/instance/uptime",
                        aggregation=agent_gcp.Aggregation(
                            per_series_aligner=Aligner.ALIGN_MAX,
                        ),
                    )
                ],
            )
        ],
    )
    agent_gcp.run(client, [], [piggy_back_section], serializer=collector)
    return list(s for s in sections if isinstance(s, agent_gcp.PiggyBackSection))


def test_can_hash_client() -> None:
    client = agent_gcp.Client({}, "test")
    assert hash(client)


def test_piggyback_identify_hosts(piggy_back_sections) -> None:
    assert piggy_back_sections[0].name == "a"
    assert piggy_back_sections[1].name == "b"


def test_serialize_piggy_back_section(piggy_back_sections, capsys) -> None:
    section = piggy_back_sections[1]
    agent_gcp.gcp_serializer([section])
    captured = capsys.readouterr()
    output = captured.out.rstrip().split("\n")
    assert output[0] == f"<<<<{section.name}>>>>"
    assert output[-1] == "<<<<>>>>"

    assert output[1] == "<<<labels:sep(0)>>>"
    assert json.loads(output[2]) == {
        "gcp/labels/van": "halen",
        "gcp/labels/judas": "priest",
        "gcp/labels/iron": "maiden",
        "gcp/project": "test",
    }

    section_names = {line[3:-3] for line in output[2:-1] if line.startswith("<<<")}
    assert section_names == {"gcp_service_testing_uptime:sep(0)"}


def test_piggy_back_sort_values_to_host(piggy_back_sections) -> None:
    # I need two sections I can compare
    assert len(piggy_back_sections) == 2
    host_a = piggy_back_sections[0]
    assert next(next(host_a.sections).results).ts.points[0].value.double_value == pytest.approx(60)
    host_b = piggy_back_sections[1]
    assert next(next(host_b.sections).results).ts.points[0].value.double_value == pytest.approx(42)


def test_piggy_back_host_labels(piggy_back_sections) -> None:
    assert piggy_back_sections[0].labels == {
        "gcp/labels/van": "halen",
        "gcp/labels/iron": "maiden",
        "gcp/labels/judas": "priest",
        "gcp/project": "test",
    }


# GCE Piggyback host tests.


@pytest.fixture(name="gce_sections")
def fixture_gce_sections() -> Sequence[agent_gcp.PiggyBackSection]:
    timeseries = [
        '{"metric": {"type": "compute.googleapis.com/instance/cpu/utilization", "labels": {}}, "resource": {"type": "gce_instance", "labels": {"project_id": "tribe29-check-development", "instance_id": "4916403162284897775"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-04-13T11:36:37.193318Z", "end_time": "2022-04-13T11:36:37.193318Z"}, "value": {"double_value": 0.0035302032187011587}}, {"interval": {"start_time": "2022-04-13T11:35:37.193318Z", "end_time": "2022-04-13T11:35:37.193318Z"}, "value": {"double_value": 0.003718815888075729}}, {"interval": {"start_time": "2022-04-13T11:34:37.193318Z", "end_time": "2022-04-13T11:34:37.193318Z"}, "value": {"double_value": 0.003641066445975986}}, {"interval": {"start_time": "2022-04-13T11:33:37.193318Z", "end_time": "2022-04-13T11:33:37.193318Z"}, "value": {"double_value":0.006292206559268394}}, {"interval": {"start_time": "2022-04-13T11:32:37.193318Z", "end_time": "2022-04-13T11:32:37.193318Z"}, "value": {"double_value": 0.006182711671318082}}, {"interval": {"start_time": "2022-04-13T11:31:37.193318Z", "end_time": "2022-04-13T11:31:37.193318Z"}, "value": {"double_value": 0.004284212986899849}}, {"interval": {"start_time": "2022-04-13T11:30:37.193318Z", "end_time": "2022-04-13T11:30:37.193318Z"}, "value": {"double_value": 0.004311434884408142}}, {"interval": {"start_time": "2022-04-13T11:29:37.193318Z", "end_time": "2022-04-13T11:29:37.193318Z"}, "value": {"double_value": 0.0035632611313867932}}, {"interval": {"start_time": "2022-04-13T11:28:37.193318Z", "end_time": "2022-04-13T11:28:37.193318Z"}, "value": {"double_value": 0.003491919276933745}}, {"interval": {"start_time": "2022-04-13T11:27:37.193318Z", "end_time": "2022-04-13T11:27:37.193318Z"}, "value": {"double_value": 0.0032100898760082743}}, {"interval": {"start_time": "2022-04-13T11:26:37.193318Z", "end_time": "2022-04-13T11:26:37.193318Z"}, "value": {"double_value": 0.003219789863135425}}, {"interval": {"start_time": "2022-04-13T11:25:37.193318Z", "end_time": "2022-04-13T11:25:37.193318Z"}, "value": {"double_value": 0.0029431110570352632}}, {"interval": {"start_time": "2022-04-13T11:24:37.193318Z", "end_time": "2022-04-13T11:24:37.193318Z"}, "value": {"double_value": 0.0029444862618781538}}, {"interval": {"start_time": "2022-04-13T11:23:37.193318Z", "end_time": "2022-04-13T11:23:37.193318Z"}, "value": {"double_value": 0.0032960633851242998}}, {"interval": {"start_time": "2022-04-13T11:22:37.193318Z", "end_time": "2022-04-13T11:22:37.193318Z"}, "value": {"double_value": 0.003308212633207426}}, {"interval": {"start_time": "2022-04-13T11:21:37.193318Z", "end_time": "2022-04-13T11:21:37.193318Z"}, "value": {"double_value": 0.0030290040189213663}}, {"interval": {"start_time": "2022-04-13T11:20:37.193318Z", "end_time": "2022-04-13T11:20:37.193318Z"}, "value": {"double_value": 0.0029890867332067472}}, {"interval": {"start_time": "2022-04-13T11:19:37.193318Z", "end_time": "2022-04-13T11:19:37.193318Z"}, "value": {"double_value": 0.0033734199011726433}}], "unit": ""}'
    ]
    assets = [
        '{"name": "//compute.googleapis.com/projects/tribe29-check-development/zones/us-central1-a/instances/instance-1", "asset_type": "compute.googleapis.com/Instance", "resource": {"version": "v1", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/compute/v1/rest", "discovery_name": "Instance", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {"deletionProtection": false, "displayDevice": {"enableDisplay": false}, "lastStartTimestamp": "2022-03-28T02:37:10.106-07:00", "creationTimestamp": "2022-03-18T06:37:06.655-07:00", "id": "4916403162284897775", "name": "instance-1", "lastStopTimestamp": "2022-04-05T01:23:00.444-07:00", "machineType": "https://www.googleapis.com/compute/v1/projects/tribe29-check-development/zones/us-central1-a/machineTypes/f1-micro", "selfLink": "https://www.googleapis.com/compute/v1/projects/tribe29-check-development/zones/us-central1-a/instances/instance-1", "tags": {"fingerprint": "42WmSpB8rSM="}, "fingerprint": "im05qPmW++Q=", "status": "TERMINATED", "shieldedInstanceIntegrityPolicy": {"updateAutoLearnPolicy": true}, "shieldedInstanceConfig": {"enableIntegrityMonitoring": true, "enableSecureBoot": false, "enableVtpm": true}, "startRestricted": false, "description": "", "confidentialInstanceConfig": {"enableConfidentialCompute": false}, "zone": "https://www.googleapis.com/compute/v1/projects/tribe29-check-development/zones/us-central1-a", "canIpForward": false, "disks": [{"type": "PERSISTENT", "boot": true, "licenses": ["https://www.googleapis.com/compute/v1/projects/debian-cloud/global/licenses/debian-10-buster"], "mode": "READ_WRITE", "index": 0.0, "source": "https://www.googleapis.com/compute/v1/projects/tribe29-check-development/zones/us-central1-a/disks/instance-1", "deviceName": "instance-1", "diskSizeGb": "10", "guestOsFeatures": [{"type": "UEFI_COMPATIBLE"}, {"type": "VIRTIO_SCSI_MULTIQUEUE"}], "interface": "SCSI", "autoDelete": true}], "cpuPlatform": "Unknown CPU Platform", "labelFingerprint": "6Ok5Ta5mo84=", "allocationAffinity": {"consumeAllocationType": "ANY_ALLOCATION"}, "networkInterfaces": [{"network": "https://www.googleapis.com/compute/v1/projects/tribe29-check-development/global/networks/default", "name": "nic0", "subnetwork": "https://www.googleapis.com/compute/v1/projects/tribe29-check-development/regions/us-central1/subnetworks/default", "networkIP": "10.128.0.2", "stackType": "IPV4_ONLY", "accessConfigs": [{"name": "External NAT", "networkTier": "PREMIUM", "type": "ONE_TO_ONE_NAT"}], "fingerprint": "h7uoBU+ZS74="}], "serviceAccounts": [{"email": "1074106860578-compute@developer.gserviceaccount.com", "scopes": ["https://www.googleapis.com/auth/devstorage.read_only", "https://www.googleapis.com/auth/logging.write", "https://www.googleapis.com/auth/monitoring.write", "https://www.googleapis.com/auth/servicecontrol", "https://www.googleapis.com/auth/service.management.readonly", "https://www.googleapis.com/auth/trace.append"]}], "scheduling": {"preemptible": false, "automaticRestart": true, "onHostMaintenance": "MIGRATE"}, "labels": {"t": "tt"}}, "location": "us-central1-a", "resource_url": ""}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-04-05T08:23:00.662291Z", "org_policy": []}'
    ]
    client = FakeClient("test", FakeMonitoringClient(timeseries), FakeAssetClient(assets))
    sections: list[agent_gcp.Section] = []
    collector = collector_factory(sections)

    agent_gcp.run(client, [], [agent_gcp.GCE], serializer=collector)
    return list(s for s in sections if isinstance(s, agent_gcp.PiggyBackSection))


def test_gce_host_labels(gce_sections: Sequence[agent_gcp.PiggyBackSection]) -> None:
    assert gce_sections[0].labels == {"gcp/labels/t": "tt", "gcp/project": "test"}


def test_gce_host_name_mangling(gce_sections: Sequence[agent_gcp.PiggyBackSection]) -> None:
    assert gce_sections[0].name == "instance-1"


def test_gce_metric_filtering(gce_sections: Sequence[agent_gcp.PiggyBackSection]) -> None:
    assert 1 == len(list(list(gce_sections[0].sections)[0].results))


@pytest.fixture(name="interval")
def _interval() -> monitoring_v3.TimeInterval:
    return monitoring_v3.TimeInterval(
        {
            "end_time": {"seconds": 100000, "nanos": 0},
            "start_time": {"seconds": (100000 - 1200), "nanos": 0},
        }
    )


def test_metric_requests(interval: monitoring_v3.TimeInterval) -> None:
    metric = agent_gcp.Metric(
        name="compute.googleapis.com/instance/uptime",
        aggregation=agent_gcp.Aggregation(
            per_series_aligner=Aligner.ALIGN_MAX, cross_series_reducer=Reducer.REDUCE_NONE
        ),
    )
    request = metric.request(interval=interval, groupby="resource.thisone", project="fun")
    expected = {
        "name": "projects/fun",
        "filter": 'metric.type = "compute.googleapis.com/instance/uptime"',
        "interval": interval,
        "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
        "aggregation": monitoring_v3.Aggregation(
            {
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.thisone"],
                "per_series_aligner": Aligner.ALIGN_MAX,
                "cross_series_reducer": Reducer.REDUCE_NONE,
            }
        ),
    }
    assert request == expected


def test_metric_requests_additional_groupby_fields(interval: monitoring_v3.TimeInterval) -> None:
    metric = agent_gcp.Metric(
        name="compute.googleapis.com/instance/uptime",
        aggregation=agent_gcp.Aggregation(
            per_series_aligner=Aligner.ALIGN_MAX,
            group_by_fields=["metric.thatone", "resource.do_not_forget_me"],
        ),
    )
    request = metric.request(interval=interval, groupby="resource.thisone", project="fun")
    expected = {
        "name": "projects/fun",
        "filter": 'metric.type = "compute.googleapis.com/instance/uptime"',
        "interval": interval,
        "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
        "aggregation": monitoring_v3.Aggregation(
            {
                "alignment_period": {"seconds": 60},
                "group_by_fields": [
                    "resource.thisone",
                    "metric.thatone",
                    "resource.do_not_forget_me",
                ],
                "per_series_aligner": Aligner.ALIGN_MAX,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            }
        ),
    }
    assert request == expected
