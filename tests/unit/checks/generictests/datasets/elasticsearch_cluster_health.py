#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "elasticsearch_cluster_health"


info = [
    ["status", "green"],
    ["number_of_nodes", "5"],
    ["unassigned_shards", "0"],
    ["number_of_pending_tasks", "0"],
    ["number_of_in_flight_fetch", "0"],
    ["timed_out", "False"],
    ["active_primary_shards", "4"],
    ["task_max_waiting_in_queue_millis", "0"],
    ["cluster_name", "My-cluster"],
    ["relocating_shards", "0"],
    ["active_shards_percent_as_number", "100.0"],
    ["active_shards", "8"],
    ["initializing_shards", "0"],
    ["number_of_data_nodes", "5"],
    ["delayed_unassigned_shards", "0"],
]


discovery = {"": [(None, {})], "shards": [(None, {})], "tasks": [(None, {})]}


checks = {
    "": [
        (
            None,
            {},
            [
                (0, "Name: My-cluster", []),
                (0, "Data nodes: 5", [("number_of_data_nodes", 5, None, None, None, None)]),
                (0, "Nodes: 5", [("number_of_nodes", 5, None, None, None, None)]),
                (0, "Status: green", []),
            ],
        )
    ],
    "shards": [
        (
            None,
            {"active_shards_percent_as_number": (100.0, 50.0)},
            [
                (0, "Active primary: 4", [("active_primary_shards", 4, None, None, None, None)]),
                (0, "Active: 8", [("active_shards", 8, None, None, None, None)]),
                (
                    0,
                    "Active in percent: 100.00%",
                    [("active_shards_percent_as_number", 100.0, None, None, None, None)],
                ),
                (
                    0,
                    "Delayed unassigned: 0",
                    [("delayed_unassigned_shards", 0, None, None, None, None)],
                ),
                (0, "Initializing: 0", [("initializing_shards", 0, None, None, None, None)]),
                (
                    0,
                    "Ongoing shard info requests: 0",
                    [("number_of_in_flight_fetch", 0, None, None, None, None)],
                ),
                (0, "Relocating: 0", [("relocating_shards", 0, None, None, None, None)]),
                (0, "Unassigned: 0", [("unassigned_shards", 0, None, None, None, None)]),
            ],
        )
    ],
    "tasks": [
        (
            None,
            {},
            [
                (
                    0,
                    "Pending tasks: 0.00",
                    [("number_of_pending_tasks", 0, None, None, None, None)],
                ),
                (
                    0,
                    "Task max waiting: 0.00",
                    [("task_max_waiting_in_queue_millis", 0, None, None, None, None)],
                ),
                (0, "Timed out: False", []),
            ],
        )
    ],
}
