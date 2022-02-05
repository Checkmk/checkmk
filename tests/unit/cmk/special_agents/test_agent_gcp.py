#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from typing import Any, Dict, Iterable

from google.auth import credentials as ga_credentials  # type: ignore[import]
from google.cloud import monitoring_v3
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


def fake_time_series(request: Dict[str, Any]) -> Iterable[TimeSeries]:
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


def test_agent_output_deserialization(mocker: MockerFixture, capsys):
    creds = ga_credentials.AnonymousCredentials()
    client = agent_gcp.Client(
        agent_gcp.monitoring_v3.MetricServiceClient(credentials=creds), "test"
    )
    mocker.patch.object(client, "list_time_series", fake_time_series)
    agent_gcp.run(client, agent_gcp.GCS)
    captured = capsys.readouterr()
    section = captured.out.split("\n")
    assert section[0] == "<<<gcp_service_gcs:sep(0)>>>"
    for line in section[1:]:
        agent_gcp.Result.deserialize(line)
