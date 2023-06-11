#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.legacy_checks.elasticsearch_cluster_health import (
    check_elasticsearch_cluster_health,
    check_elasticsearch_cluster_health_shards,
    check_elasticsearch_cluster_health_tasks,
    parse_elasticsearch_cluster_health,
)

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "parameters, item, info, expected_result",
    [
        (
            {},
            None,
            [
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
            ],
            [
                (0, "Name: elasticsearch"),
                (0, "Data nodes: 5", [("number_of_data_nodes", 5, None, None)]),
                (0, "Nodes: 5", [("number_of_nodes", 5, None, None)]),
                (1, "Status: yellow"),
            ],
        ),
        (
            {"green": 0, "red": 2, "yellow": 3},
            None,
            [["status", "yellow"]],
            [
                (3, "Status: yellow (State changed by rule)"),
            ],
        ),
    ],
)
def test_check_function(parameters, item, info, expected_result):
    parsed = parse_elasticsearch_cluster_health(info)
    assert list(check_elasticsearch_cluster_health(item, parameters, parsed)) == expected_result


@pytest.mark.parametrize(
    "parameters, item, info, expected_result",
    [
        (
            {},
            None,
            [
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
            ],
            [
                (0, "Active primary: 747", [("active_primary_shards", 747, None, None)]),
                (0, "Active: 1613", [("active_shards", 1613, None, None)]),
                (
                    0,
                    "Active in percent: 100.00%",
                    [("active_shards_percent_as_number", 100.0, None, None)],
                ),
                (0, "Delayed unassigned: 0", [("delayed_unassigned_shards", 0, None, None)]),
                (0, "Initializing: 0", [("initializing_shards", 0, None, None)]),
                (
                    0,
                    "Ongoing shard info requests: 0",
                    [("number_of_in_flight_fetch", 0, None, None)],
                ),
                (0, "Relocating: 0", [("relocating_shards", 0, None, None)]),
                (0, "Unassigned: 0", [("unassigned_shards", 0, None, None)]),
            ],
        ),
        (
            {},
            None,
            [
                ["cluster_name", "elasticsearch"],
                ["status", "yellow"],
                ["timed_out", "False"],
                ["number_of_nodes", "5"],
                ["number_of_data_nodes", "5"],
                ["number_of_pending_tasks", "0"],
                ["task_max_waiting_in_queue_millis", "0"],
            ],
            [],  # If there is no shards information, there is no result (the state of the check turns to UNKNOWN)
        ),
    ],
)
def test_shards_check_function(parameters, item, info, expected_result):
    parsed = parse_elasticsearch_cluster_health(info)
    assert (
        list(check_elasticsearch_cluster_health_shards(item, parameters, parsed)) == expected_result
    )


@pytest.mark.parametrize(
    "parameters, item, info, expected_result",
    [
        (
            {},
            None,
            [
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
            ],
            [
                (0, "Pending tasks: 0.00", [("number_of_pending_tasks", 0, None, None)]),
                (
                    0,
                    "Task max waiting: 0.00",
                    [("task_max_waiting_in_queue_millis", 0, None, None)],
                ),
                (0, "Timed out: False"),
            ],
        ),
        (
            {},
            None,
            [
                ["cluster_name", "elasticsearch"],
                ["status", "yellow"],
                ["number_of_nodes", "5"],
                ["number_of_data_nodes", "5"],
            ],
            [],  # If there is no tasks information, there is no result (the state of the check turns to UNKNOWN)
        ),
    ],
)
def test_tasks_check_function(parameters, item, info, expected_result):
    parsed = parse_elasticsearch_cluster_health(info)
    assert (
        list(check_elasticsearch_cluster_health_tasks(item, parameters, parsed)) == expected_result
    )
