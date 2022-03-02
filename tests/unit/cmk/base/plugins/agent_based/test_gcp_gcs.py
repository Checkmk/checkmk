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

SECTION_TABLE = [
    [
        '[{"name":"backup-home-ml-free"},{"name":"gcf-sources-360989076580-us-central1"},{"name":"lakjsdklasjd"},{"name":"us.artifacts.backup-255820.appspot.com"}]'
    ],
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


def test_parse_gcp():
    section = parse_gcp_gcs(SECTION_TABLE)
    n_rows = sum(len(i.rows) for i in section.values())
    # first row contains general section information and no metrics
    assert n_rows == len(SECTION_TABLE) - 1


@pytest.fixture(name="section")
def fixture_section():
    return parse_gcp_gcs(SECTION_TABLE)


def test_item_without_data_is_invalid(section):
    for name, item in section.items():
        if name == "nodata":
            assert not item.is_valid


@pytest.fixture(name="buckets")
def fixture_buckets(section):
    return sorted(list(discover(section)))


def test_discover_two_buckets(buckets: Sequence[Service]):
    assert len(buckets) == 4
    assert {b.item for b in buckets} == {
        "backup-home-ml-free",
        "lakjsdklasjd",
        "gcf-sources-360989076580-us-central1",
        "us.artifacts.backup-255820.appspot.com",
    }


def test_discover_project_labels(buckets: Sequence[Service]):
    for bucket in buckets:
        assert ServiceLabel("gcp_project_id", "backup-255820") in bucket.labels


def test_discover_bucket_labels(buckets: Sequence[Service]):
    labels = buckets[0].labels
    assert len(labels) == 2
    assert ServiceLabel("gcp_bucket_name", "backup-home-ml-free") in labels


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
def fixture_results(checkplugin, section):
    params = {k: None for k in checkplugin.metrics}
    results = list(checkplugin.function(item=ITEM, params=params, section=section))
    return results, checkplugin


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
    def test_zero_default_if_metric_does_not_exist(self, section):
        params = {k: None for k in ["requests"]}
        results = (
            el
            for el in check_gcp_gcs_requests(item=ITEM, params=params, section=section)
            if isinstance(el, Metric)
        )
        for result in results:
            assert result.value == 0.0

    # objects does contain example data
    def test_non_zero_if_metric_exist(self, section):
        params = {k: None for k in ["aws_bucket_size", "aws_num_objects"]}
        results = (
            el
            for el in check_gcp_gcs_object(item=ITEM, params=params, section=section)
            if isinstance(el, Metric)
        )
        for result in results:
            assert result.value != 0.0


class TestConfiguredNotificationLevels:
    # In the example sections we do not have data for all metrics. To be able to test all check plugins
    # use 0, the default value, to check notification levels.
    def test_warn_levels(self, checkplugin, section):
        params = {k: (0, None) for k in checkplugin.metrics}
        results = list(checkplugin.function(item=ITEM, params=params, section=section))
        results = [r for r in results if isinstance(r, Result)]
        for r in results:
            assert r.state == State.WARN

    def test_crit_levels(self, checkplugin, section):
        params = {k: (None, 0) for k in checkplugin.metrics}
        results = list(checkplugin.function(item=ITEM, params=params, section=section))
        results = [r for r in results if isinstance(r, Result)]
        for r in results:
            assert r.state == State.CRIT
