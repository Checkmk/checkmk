#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import json
from typing import Optional

import pytest
from google.cloud import monitoring_v3
from google.cloud.monitoring_v3.types import TimeSeries

from cmk.base.api.agent_based.checking_classes import ServiceLabel
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.gcp_run import (
    check_gcp_run_cpu,
    check_gcp_run_memory,
    check_gcp_run_network,
    check_gcp_run_requests,
    discover,
    parse_gcp_run,
)
from cmk.base.plugins.agent_based.utils import gcp

from cmk.special_agents import agent_gcp

from .gcp_test_util import DiscoverTester, ParsingTester, Plugin

ASSET_TABLE = [
    ['{"project":"backup-255820", "config":["cloud_run"]}'],
    [
        '{"name": "//run.googleapis.com/projects/backup-255820/locations/us-central1/services/aaaa", "asset_type": "run.googleapis.com/Service", "resource": {"version": "v1", "discovery_document_uri": "https://run.googleapis.com/$discovery/rest", "discovery_name": "Service", "parent": "//cloudresourcemanager.googleapis.com/projects/360989076580", "data": {"metadata": {"name": "aaaa", "generation": 1.0, "uid": "e95937c6-9864-458b-acea-9147be027604", "namespace": "360989076580", "labels": {"cloud.googleapis.com/location": "us-central1"}, "selfLink": "/apis/serving.knative.dev/v1/namespaces/360989076580/services/aaaa", "creationTimestamp": "2022-02-17T14:12:58.71874Z", "annotations": {"run.googleapis.com/ingress-status": "all", "client.knative.dev/user-image": "us-docker.pkg.dev/cloudrun/container/hello", "run.googleapis.com/client-name": "cloud-console", "serving.knative.dev/creator": "max.linke88@gmail.com", "serving.knative.dev/lastModifier": "max.linke88@gmail.com", "run.googleapis.com/ingress": "all"}, "resourceVersion": "AAXYN2StUX8"}, "spec": {"traffic": [{"latestRevision": true, "percent": 100.0}], "template": {"spec": {"serviceAccountName": "360989076580-compute@developer.gserviceaccount.com", "timeoutSeconds": 300.0, "containers": [{"resources": {"limits": {"memory": "512Mi", "cpu": "1000m"}}, "ports": [{"containerPort": 8080.0, "name": "http1"}], "image": "us-docker.pkg.dev/cloudrun/container/hello"}], "containerConcurrency": 80.0}, "metadata": {"name": "aaaa-00001-qax", "annotations": {"autoscaling.knative.dev/maxScale": "4", "run.googleapis.com/client-name": "cloud-console"}}}}, "status": {"url": "https://aaaa-l2ihgnbm5q-uc.a.run.app", "conditions": [{"status": "True", "lastTransitionTime": "2022-02-17T14:15:07.434367Z", "type": "Ready"}, {"type": "ConfigurationsReady", "status": "True", "lastTransitionTime": "2022-02-17T14:15:07.124653Z"}, {"status": "True", "lastTransitionTime": "2022-02-17T14:15:07.434367Z", "type": "RoutesReady"}], "latestReadyRevisionName": "aaaa-00001-qax", "address": {"url": "https://aaaa-l2ihgnbm5q-uc.a.run.app"}, "observedGeneration": 1.0, "latestCreatedRevisionName": "aaaa-00001-qax", "traffic": [{"latestRevision": true, "revisionName": "aaaa-00001-qax", "percent": 100.0}]}, "apiVersion": "serving.knative.dev/v1", "kind": "Service"}, "location": "us-central1", "resource_url": ""}, "ancestors": ["projects/360989076580"], "update_time": "2022-02-17T14:15:07.434367Z", "org_policy": []}'
    ],
]


class TestDiscover(DiscoverTester):
    @property
    def _assets(self) -> StringTable:
        return ASSET_TABLE

    @property
    def expected_services(self) -> set[str]:
        return {
            "aaaa",
        }

    @property
    def expected_labels(self) -> set[ServiceLabel]:
        return {
            ServiceLabel("gcp/location", "us-central1"),
            ServiceLabel("gcp/run/name", "aaaa"),
            ServiceLabel("gcp/projectId", "backup-255820"),
        }

    def discover(self, assets: Optional[gcp.AssetSection]) -> DiscoveryResult:
        yield from discover(section_gcp_service_cloud_run=None, section_gcp_assets=assets)


def generate_timeseries(item: str, value: float) -> StringTable:
    start_time = datetime.datetime(2016, 4, 6, 22, 5, 0, 42)
    end_time = datetime.datetime(2016, 4, 6, 22, 5, 1, 42)
    interval = monitoring_v3.TimeInterval(end_time=end_time, start_time=start_time)
    point = monitoring_v3.Point({"interval": interval, "value": {"double_value": value}})
    metric_labels = ["2xx", "3xx", "4xx", "5xx"]

    time_series = []
    for metric in agent_gcp.RUN.metrics:
        metric_type = metric.name
        resource_labels = {"project": "test", agent_gcp.RUN.default_groupby.split(".", 1)[-1]: item}
        if metric.aggregation.group_by_fields:
            for label_value in metric_labels:
                metric_label = {
                    metric.aggregation.group_by_fields[0].split(".", 1)[-1]: label_value
                }
                ts = monitoring_v3.TimeSeries(
                    {
                        "metric": {"type": metric_type, "labels": metric_label},
                        "resource": {"type": "does_not_matter_i_think", "labels": resource_labels},
                        "metric_kind": 1,
                        "value_type": 3,
                        "points": [point],
                    }
                )
                time_series.append(ts)
        else:
            ts = monitoring_v3.TimeSeries(
                {
                    "metric": {"type": metric_type, "labels": {}},
                    "resource": {"type": "does_not_matter_i_think", "labels": resource_labels},
                    "metric_kind": 1,
                    "value_type": 3,
                    "points": [point],
                }
            )
            time_series.append(ts)

    return [[json.dumps(TimeSeries.to_dict(ts))] for ts in time_series]


class TestParsing(ParsingTester):
    def parse(self, string_table):
        return parse_gcp_run(string_table)

    @property
    def section_table(self) -> StringTable:
        return generate_timeseries("item", 42.0)


PLUGINS = [
    pytest.param(
        Plugin(
            function=check_gcp_run_cpu,
            metrics=["util"],
            results=[Result(state=State.OK, summary="CPU: 4200.00%")],
        ),
        id="cpu",
    ),
    pytest.param(
        Plugin(
            function=check_gcp_run_memory,
            metrics=["memory_util"],
            results=[Result(state=State.OK, summary="Memory: 4200.00%")],
        ),
        id="memory",
    ),
    pytest.param(
        Plugin(
            function=check_gcp_run_network,
            metrics=["net_data_sent", "net_data_recv"],
            results=[
                Result(state=State.OK, summary="In: 336 Bit/s"),
                Result(state=State.OK, summary="Out: 336 Bit/s"),
            ],
        ),
        id="network",
    ),
    pytest.param(
        Plugin(
            function=check_gcp_run_requests,
            metrics=[
                "faas_total_instance_count",
                "faas_execution_count",
                "faas_execution_count_2xx",
                "faas_execution_count_3xx",
                "faas_execution_count_4xx",
                "faas_execution_count_5xx",
                "faas_execution_times",
                "gcp_billable_time",
            ],
            results=[
                Result(state=State.OK, summary="Billable time: 42.00 s/s"),
                Result(state=State.OK, summary="Instances: 42.0"),
                Result(state=State.OK, summary="Latencies: 42 milliseconds"),
                Result(state=State.OK, summary="Requests 2xx (sucess): 42.0"),
                Result(state=State.OK, summary="Requests 3xx (redirection): 42.0"),
                Result(state=State.OK, summary="Requests 4xx (client error): 42.0"),
                Result(state=State.OK, summary="Requests 5xx (server error): 42.0"),
                Result(state=State.OK, summary="Requests: 168.0"),
            ],
        ),
        id="requests",
    ),
]


def generate_results(plugin: Plugin) -> CheckResult:
    item = "item"
    section = parse_gcp_run(generate_timeseries(item, 42))
    yield from plugin.function(
        item=item,
        params={k: None for k in plugin.metrics},
        section_gcp_service_cloud_run=section,
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
