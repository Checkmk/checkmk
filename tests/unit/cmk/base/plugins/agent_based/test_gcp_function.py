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
from cmk.base.plugins.agent_based.gcp_function import (
    check_gcp_function_egress,
    check_gcp_function_execution,
    check_gcp_function_instances,
    discover,
    parse_gcp_function,
)

SECTION_TABLE = [
    ['[{"name":"function-1"},{"name":"function-2"},{"name":"function-3"}]'],
    [
        '{"metric":{"type":"cloudfunctions.googleapis.com/function/execution_count","labels":{}},"resource":{"type":"cloud_function","labels":{"project_id":"backup-255820","function_name":"function-2"}},"metricKind":1,"valueType":3,"points":[{"interval":{"startTime":"2022-02-23T12:27:27.205842Z","endTime":"2022-02-23T12:27:27.205842Z"},"value":{"doubleValue":0.016666666666666666}},{"interval":{"startTime":"2022-02-23T12:26:27.205842Z","endTime":"2022-02-23T12:26:27.205842Z"},"value":{"doubleValue":0.06666666666666667}}],"unit":""}'
    ],
    [
        '{"metric":{"type":"cloudfunctions.googleapis.com/function/user_memory_bytes","labels":{}},"resource":{"type":"cloud_function","labels":{"project_id":"backup-255820","function_name":"function-2"}},"metricKind":1,"valueType":3,"points":[{"interval":{"startTime":"2022-02-23T12:27:27.205842Z","endTime":"2022-02-23T12:27:27.205842Z"},"value":{"doubleValue":63722624.968750365}}],"unit":""}'
    ],
    [
        '{"metric":{"type":"cloudfunctions.googleapis.com/function/execution_times","labels":{}},"resource":{"type":"cloud_function","labels":{"project_id":"backup-255820","function_name":"function-2"}},"metricKind":1,"valueType":3,"points":[{"interval":{"startTime":"2022-02-23T12:26:27.205842Z","endTime":"2022-02-23T12:26:27.205842Z"},"value":{"doubleValue":77468035.78821974}}],"unit":""}'
    ],
    [
        '{"metric":{"type":"cloudfunctions.googleapis.com/function/active_instances","labels":{}},"resource":{"type":"cloud_function","labels":{"project_id":"backup-255820","function_name":"function-2"}},"metricKind":1,"valueType":2,"points":[{"interval":{"startTime":"2022-02-23T12:27:27.205842Z","endTime":"2022-02-23T12:27:27.205842Z"},"value":{"int64Value":"3"}}],"unit":""}'
    ],
    [
        '{"metric":{"type":"cloudfunctions.googleapis.com/function/active_instances","labels":{}},"resource":{"type":"cloud_function","labels":{"project_id":"backup-255820","function_name":"function-3"}},"metricKind":1,"valueType":2,"points":[{"interval":{"startTime":"2022-02-23T12:27:27.205842Z","endTime":"2022-02-23T12:27:27.205842Z"},"value":{"int64Value":"3"}}],"unit":""}'
    ],
]


def test_parse_gcp():
    section = parse_gcp_function(SECTION_TABLE)
    n_rows = sum(len(i.rows) for i in section.values())
    # first row contains general section information and no metrics
    assert n_rows == len(SECTION_TABLE) - 1


@pytest.fixture(name="section")
def fixture_section():
    return parse_gcp_function(SECTION_TABLE)


def test_item_without_data_is_invalid(section):
    for name, item in section.items():
        if name == "nodata":
            assert not item.is_valid


@pytest.fixture(name="functions")
def fixture_functions(section):
    return sorted(list(discover(section)))


def test_discover_two_functions(functions: Sequence[Service]):
    assert len(functions) == 2
    assert {b.item for b in functions} == {"function-2", "function-3"}


def test_discover_project_labels(functions: Sequence[Service]):
    for bucket in functions:
        assert ServiceLabel("gcp_project_id", "backup-255820") in bucket.labels


def test_discover_bucket_labels(functions: Sequence[Service]):
    labels = functions[0].labels
    assert len(labels) == 2
    assert ServiceLabel("gcp_function_name", "function-2") in labels


@dataclass(frozen=True)
class Plugin:
    metrics: Sequence[str]
    function: Callable


PLUGINS = [
    Plugin(
        function=check_gcp_function_egress,
        metrics=[
            "net_data_sent",
        ],
    ),
    Plugin(
        function=check_gcp_function_execution,
        metrics=["faas_execution_count", "aws_lambda_memory_size_absolute", "faas_execution_times"],
    ),
    Plugin(
        function=check_gcp_function_instances,
        metrics=[
            "faas_total_instance_count",
            "faas_active_instance_count",
        ],
    ),
]
ITEM = "function-3"


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
            for el in check_gcp_function_instances(item=ITEM, params=params, section=section)
            if isinstance(el, Metric)
        )
        for result in results:
            assert result.value == 0.0


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
