#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
import json
from dataclasses import dataclass
from typing import Any, Iterable, List, Sequence

import pytest
from google.cloud import asset_v1, monitoring_v3
from google.cloud.monitoring_v3.types import TimeSeries
from pytest_mock import MockerFixture

from cmk.special_agents import agent_gcp

METRIC_TYPE = "compute.googleapis.com/instance/uptime"
METRIC_LABELS = {"instance_name": "instance-1"}
METRIC_LABELS2 = {"instance_name": "instance-2"}

RESOURCE_TYPE = "gce_instance"
RESOURCE_LABELS = {
    "project_id": "my-project",
    "zone": "us-east1-a",
    "instance_id": "1234567890123456789",
}
RESOURCE_LABELS2 = {
    "project_id": "my-project",
    "zone": "us-east1-b",
    "instance_id": "9876543210987654321",
}

METRIC_KIND = "DELTA"
VALUE_TYPE = "DOUBLE"

TS0 = datetime.datetime(2016, 4, 6, 22, 5, 0, 42)
TS1 = datetime.datetime(2016, 4, 6, 22, 5, 1, 42)
TS2 = datetime.datetime(2016, 4, 6, 22, 5, 2, 42)


class FakeMonitoringClient:
    def list_time_series(self, request: Any) -> Iterable[TimeSeries]:
        def _make_interval(end_time, start_time):
            interval = monitoring_v3.TimeInterval(end_time=end_time, start_time=start_time)
            return interval

        INTERVAL1 = _make_interval(TS1, TS0)
        INTERVAL2 = _make_interval(TS2, TS1)

        VALUE1 = 60  # seconds
        VALUE2 = 60.001  # seconds

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


class FakeAssetClient:
    def list_assets(self, request: Any) -> Iterable[asset_v1.Asset]:
        yield asset_v1.Asset(name="1")
        yield asset_v1.Asset(name="2")


@dataclass(frozen=True)
class FakeBucket:
    name: str


class FakeStorageClient:
    def list_buckets(self) -> List[FakeBucket]:
        return [FakeBucket("Fake"), FakeBucket("Almost Real")]


@dataclass(frozen=True)
class FakeFunction:
    name: str


class FakeFunctionClient:
    def list_functions(self, request: Any) -> Sequence[FakeFunction]:
        return [FakeFunction("a"), FakeFunction("b")]


class FakeRunClient:
    def list_services(self, parent: Any):
        return dict(items=[dict(metadata=dict(name="a"))])


Section = Sequence[str]


@pytest.fixture(name="agent_output")
def fixture_agent_output(mocker: MockerFixture, capsys) -> Section:
    client = agent_gcp.Client({}, "test")
    mocker.patch.object(client, "monitoring", FakeMonitoringClient)
    mocker.patch.object(client, "asset", FakeAssetClient)
    mocker.patch.object(client, "storage", FakeStorageClient)
    mocker.patch.object(client, "functions", FakeFunctionClient)
    mocker.patch.object(client, "run", FakeRunClient)
    agent_gcp.run(client, list(agent_gcp.SERVICES.values()))
    captured = capsys.readouterr()
    # strip trailing new lines
    sections = captured.out.rstrip().split("\n")
    return sections


def test_output_contains_defined_metric_sections(agent_output: Section):
    metrics = [l for l in agent_output if l.startswith("<<<gcp_service")]
    names = {m.removeprefix("<<<gcp_service_").removesuffix(":sep(0)>>>") for m in metrics}
    assert names == {s.name for s in agent_gcp.SERVICES.values()}


def test_output_contains_one_asset_section(agent_output: Section):
    assets = [l for l in agent_output if l == "<<<gcp_assets:sep(0)>>>"]
    assert len(assets) == 1


@pytest.fixture(name="sections")
def fixture_section(agent_output: Section) -> Sequence[Section]:
    sections = []
    section = [
        agent_output[0],
    ]
    for line in agent_output[1:]:
        if line.startswith("<<<"):
            sections.append(section.copy())
            section = []
        section.append(line)
    sections.append(section.copy())
    return sections


def test_sections_contain_json(sections: Sequence[Section]):
    for section in sections:
        for line in section[1:]:
            json.loads(line)


def test_metric_deserialization(sections: Sequence[Section]):
    for section in sections:
        if not section[0].startswith("<<<gcp_service"):
            continue
        # the first line is some asset information. Do not test anymore will be replaced soon
        for line in section[2:]:
            agent_gcp.Result.deserialize(line)


def test_asset_deserialization(sections: Sequence[Section]):
    for section in sections:
        if not section[0].startswith("<<<gcp_assets"):
            continue
        assert json.loads(section[1]) == {"project": "test"}
        for line in section[2:]:
            agent_gcp.Asset.deserialize(line)


def test_can_hash_client():
    client = agent_gcp.Client({}, "test")
    assert hash(client)
