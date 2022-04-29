#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
import json
from typing import Any, Iterable, Sequence

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


def collector_factory(container: list[agent_gcp.Section]):
    def f(sections: Iterable[agent_gcp.Section]):
        container.extend(list(sections))

    return f


@pytest.fixture(name="agent_output")
def fixture_agent_output(mocker: MockerFixture) -> Sequence[agent_gcp.Section]:
    client = agent_gcp.Client({}, "test")
    mocker.patch.object(client, "monitoring", FakeMonitoringClient)
    mocker.patch.object(client, "asset", FakeAssetClient)
    sections: list[agent_gcp.Section] = []
    collector = collector_factory(sections)
    agent_gcp.run(client, list(agent_gcp.SERVICES.values()), serializer=collector)
    return list(sections)


def test_output_contains_defined_metric_sections(agent_output: Sequence[agent_gcp.Section]):
    names = {s.name for s in agent_output}
    assert names.issuperset({s.name for s in agent_gcp.SERVICES.values()})


def test_output_contains_one_asset_section(agent_output: Sequence[agent_gcp.Section]):
    assert "asset" in {s.name for s in agent_output}


def test_metric_serialization(agent_output: Sequence[agent_gcp.Section], capsys):
    result_section = next(s for s in agent_output if isinstance(s, agent_gcp.ResultSection))
    agent_gcp.gcp_serializer([result_section])
    captured = capsys.readouterr()
    lines = captured.out.rstrip().split("\n")
    assert lines[0] == f"<<<gcp_service_{result_section.name}:sep(0)>>>"
    for line in lines[1:]:
        agent_gcp.Result.deserialize(line)


def test_asset_serialization(agent_output: Sequence[agent_gcp.Section], capsys):
    asset_section = next(s for s in agent_output if isinstance(s, agent_gcp.AssetSection))
    agent_gcp.gcp_serializer([asset_section])
    captured = capsys.readouterr()
    lines = captured.out.rstrip().split("\n")
    assert lines[0] == "<<<gcp_assets:sep(0)>>>"
    assert json.loads(lines[1]) == {"project": "test"}
    for line in lines[2:]:
        agent_gcp.Asset.deserialize(line)


def test_can_hash_client():
    client = agent_gcp.Client({}, "test")
    assert hash(client)
