#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, timezone

import pytest
from kubernetes.client.models import V1Node, V1ObjectMeta  # type: ignore[import]

from cmk.special_agents.agent_kubernetes import Node, NodeList


def create_node(name, timestamp):
    stats_template = '{"stats": [{"timestamp": "%s"}]}'
    return Node(V1Node(metadata=V1ObjectMeta(name=name)), stats_template % timestamp)


def cluster_stats(node_names, stat_timestamps):
    nodes = NodeList(
        [create_node(name, timestamp) for name, timestamp in zip(node_names, stat_timestamps)]
    )
    return nodes.cluster_stats()


def test_node_timestamps_utc():
    node_names = ["node1", "node2", "node3"]
    stat_time_formatted = [
        "2019-02-15T13:53:27.825541873Z",
        "2019-02-15T13:53:29.796754852Z",
        "2019-02-15T13:53:20.663979637Z",
    ]

    stats = cluster_stats(node_names, stat_time_formatted)
    utc_timestamp_average = 1550238806.0954247
    assert stats["timestamp"] == pytest.approx(
        utc_timestamp_average
    ), "The timestamp of a cluster has to be the average timestamp of its nodes"


def test_node_timestamps_non_utc():
    node_names = ["node1", "node2", "node3"]
    stat_time_formatted = [
        "2019-03-01T10:44:58.19881199+01:00",
        "2019-03-01T10:44:55.383089539+01:00",
        "2019-03-01T10:44:51.42243614+01:00",
    ]

    stats = cluster_stats(node_names, stat_time_formatted)
    utc_timestamp_average = 1551433495.0014455
    assert stats["timestamp"] == pytest.approx(
        utc_timestamp_average
    ), "The timestamp of a cluster has to be the average timestamp of its nodes"


@pytest.mark.parametrize(
    "metadata, parsed_time",
    [
        (
            V1ObjectMeta(
                name="mynode",
                namespace="foo",
                creation_timestamp=datetime(2021, 5, 12, 10, 22, 39, 0, timezone.utc),
            ),
            1620814959.0,
        ),
    ],
)
def test_node_metadata_creation_timestamp(metadata, parsed_time):
    assert Node(V1Node(metadata=metadata), "").creation_timestamp == parsed_time


@pytest.mark.parametrize(
    "raw_node_stats, parsed_stats",
    [
        (
            "{'name': '/', 'subcontainers': [{'name': '/kubepods.slice'}, {'name': '/system.slice'}, {'name': '/user.slice'}], \
        'spec': {'creation_time': '2021-05-12T10:22:39.7Z', 'has_cpu': True, 'cpu': {'limit': 1024, 'max_limit': 0, 'mask': '0', 'period': 100000}, \
        'has_memory': True, 'memory': {'limit': 1031061504, 'reservation': 9223372036854771712}, 'has_network': True, 'has_filesystem': True, \
        'has_diskio': True, 'has_custom_metrics': False}, 'stats': [{'timestamp': '2021-05-13T05:10:46.841389081Z', \
        'cpu': {'usage': {'total': 2607117792227, 'user': 00, 'system': 00}, \
        'cfs': {'periods': 0, 'throttled_periods': 0, 'throttled_time': 0}, 'schedstat': {'run_time': 0, 'runqueue_time': 0, 'run_periods': 0}, \
        'load_average': 0}, 'diskio': {'io_service_bytes': [{'device': '/dev/xvda', 'major': 202, 'minor': 0, \
        'stats': {'Async': 67497, 'Read': 2770, 'Sync': 5617, 'Total': 73114, 'Write': 70344}}]}, \
        'memory': {'usage': 660123648, 'max_usage': 872337408, 'cache': 462823424, 'rss': 197300224, 'swap': 0, 'mapped_file': 2, \
        'working_set': 401657856, 'failcnt': 0, 'container_data': {'pgfault': 1, 'pgmajfault': 9}, \
        'hierarchical_data': {'pgfault': 1, 'pgmajfault': 9}}, \
        'task_stats': {'nr_sleeping': 0, 'nr_running': 0, 'nr_stopped': 0, 'nr_uninterruptible': 0, 'nr_io_wait': 0}, \
        'processes': {'process_count': 0, 'fd_count': 0}}]}",
            {
                "cpu": {
                    "cfs": {"periods": 0, "throttled_periods": 0, "throttled_time": 0},
                    "load_average": 0,
                    "schedstat": {"run_periods": 0, "run_time": 0, "runqueue_time": 0},
                    "usage": {"system": 00, "total": 2607117792227, "user": 00},
                },
                "diskio": {
                    "io_service_bytes": [
                        {
                            "device": "/dev/xvda",
                            "major": 202,
                            "minor": 0,
                            "stats": {
                                "Async": 67497,
                                "Read": 2770,
                                "Sync": 5617,
                                "Total": 73114,
                                "Write": 70344,
                            },
                        }
                    ]
                },
                "memory": {
                    "cache": 462823424,
                    "container_data": {"pgfault": 1, "pgmajfault": 9},
                    "failcnt": 0,
                    "hierarchical_data": {"pgfault": 1, "pgmajfault": 9},
                    "mapped_file": 2,
                    "max_usage": 872337408,
                    "rss": 197300224,
                    "swap": 0,
                    "usage": 660123648,
                    "working_set": 401657856,
                },
                "processes": {"fd_count": 0, "process_count": 0},
                "task_stats": {
                    "nr_io_wait": 0,
                    "nr_running": 0,
                    "nr_sleeping": 0,
                    "nr_stopped": 0,
                    "nr_uninterruptible": 0,
                },
                "timestamp": 1620882646.841389,
            },
        ),
    ],
)
def test_init_node_stats(raw_node_stats, parsed_stats):
    assert Node(V1Node(metadata=V1ObjectMeta(name="mynode")), raw_node_stats).stats == parsed_stats
