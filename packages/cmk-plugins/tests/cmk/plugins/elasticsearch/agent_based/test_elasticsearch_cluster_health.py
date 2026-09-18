#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.plugins.elasticsearch.agent_based.elasticsearch_cluster_health import (
    check_elasticsearch_cluster_health,
    check_elasticsearch_cluster_health_shards,
    check_elasticsearch_cluster_health_tasks,
    parse_elasticsearch_cluster_health,
)

_FULL_STRING_TABLE: list[list[str]] = [
    ["cluster_name", "elasticsearch"],
    ["status", "yellow"],
    ["timed_out", "False"],
    ["number_of_nodes", "5"],
    ["number_of_data_nodes", "5"],
    ["active_primary_shards", "747"],
    ["active_shards", "1613"],
    ["relocating_shards", "0"],
    ["initializing_shards", "0"],
    ["unassigned_shards", "0"],
    ["delayed_unassigned_shards", "0"],
    ["number_of_pending_tasks", "0"],
    ["number_of_in_flight_fetch", "0"],
    ["task_max_waiting_in_queue_millis", "0"],
    ["active_shards_percent_as_number", "100.0"],
]


@pytest.mark.parametrize(
    "parameters, info, expected_result",
    [
        (
            {},
            _FULL_STRING_TABLE,
            [
                Result(state=State.OK, summary="Name: elasticsearch"),
                Result(state=State.OK, summary="Data nodes: 5"),
                Metric("number_of_data_nodes", 5.0),
                Result(state=State.OK, summary="Nodes: 5"),
                Metric("number_of_nodes", 5.0),
                Result(state=State.WARN, summary="Status: yellow"),
            ],
        ),
        (
            {"green": 0, "red": 2, "yellow": 3},
            [["status", "yellow"]],
            [
                Result(state=State(3), summary="Status: yellow (State changed by rule)"),
            ],
        ),
    ],
)
def test_check_function(
    parameters: Mapping[str, object], info: StringTable, expected_result: list[Result | Metric]
) -> None:
    parsed = parse_elasticsearch_cluster_health(info)
    assert list(check_elasticsearch_cluster_health(parameters, parsed)) == expected_result


@pytest.mark.parametrize(
    "parameters, info, expected_result",
    [
        (
            {},
            _FULL_STRING_TABLE,
            [
                Result(state=State.OK, summary="Active primary: 747"),
                Metric("active_primary_shards", 747.0),
                Result(state=State.OK, summary="Active: 1613"),
                Metric("active_shards", 1613.0),
                Result(state=State.OK, summary="Active in percent: 100.00%"),
                Metric("active_shards_percent_as_number", 100.0),
                Result(state=State.OK, summary="Delayed unassigned: 0"),
                Metric("delayed_unassigned_shards", 0.0),
                Result(state=State.OK, summary="Initializing: 0"),
                Metric("initializing_shards", 0.0),
                Result(state=State.OK, summary="Ongoing shard info requests: 0"),
                Metric("number_of_in_flight_fetch", 0.0),
                Result(state=State.OK, summary="Relocating: 0"),
                Metric("relocating_shards", 0.0),
                Result(state=State.OK, summary="Unassigned: 0"),
                Metric("unassigned_shards", 0.0),
            ],
        ),
        (
            {},
            [
                ["cluster_name", "elasticsearch"],
                ["status", "yellow"],
                ["timed_out", "False"],
                ["number_of_nodes", "5"],
                ["number_of_data_nodes", "5"],
                ["number_of_pending_tasks", "0"],
                ["task_max_waiting_in_queue_millis", "0"],
            ],
            [],
        ),
    ],
)
def test_shards_check_function(
    parameters: Mapping[str, object], info: StringTable, expected_result: list[Result | Metric]
) -> None:
    parsed = parse_elasticsearch_cluster_health(info)
    assert list(check_elasticsearch_cluster_health_shards(parameters, parsed)) == expected_result


@pytest.mark.parametrize(
    "parameters, info, expected_result",
    [
        (
            {},
            _FULL_STRING_TABLE,
            [
                Result(state=State.OK, summary="Pending tasks: 0.00"),
                Metric("number_of_pending_tasks", 0.0),
                Result(state=State.OK, summary="Task max waiting: 0.00"),
                Metric("task_max_waiting_in_queue_millis", 0.0),
                Result(state=State.OK, summary="Timed out: False"),
            ],
        ),
        (
            {},
            [
                ["cluster_name", "elasticsearch"],
                ["status", "yellow"],
                ["number_of_nodes", "5"],
                ["number_of_data_nodes", "5"],
            ],
            [],
        ),
    ],
)
def test_tasks_check_function(
    parameters: Mapping[str, object], info: StringTable, expected_result: list[Result | Metric]
) -> None:
    parsed = parse_elasticsearch_cluster_health(info)
    assert list(check_elasticsearch_cluster_health_tasks(parameters, parsed)) == expected_result
