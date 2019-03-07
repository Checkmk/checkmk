# encoding: utf-8

import pytest
from kubernetes.client.models import V1ObjectMeta, V1Node

from cmk.special_agents.agent_kubernetes import Node, NodeList


def create_node(name, timestamp):
    stats_template = u'{"stats": [{"timestamp": "%s"}]}'
    return Node(V1Node(metadata=V1ObjectMeta(name=name)), stats_template % timestamp)


def cluster_stats(node_names, stat_timestamps):
    nodes = NodeList(
        [create_node(name, timestamp) for name, timestamp in zip(node_names, stat_timestamps)])
    return nodes.cluster_stats()


def test_node_timestamps_utc():
    node_names = ['node1', 'node2', 'node3']
    stat_time_formatted = [
        '2019-02-15T13:53:27.825541873Z',
        '2019-02-15T13:53:29.796754852Z',
        '2019-02-15T13:53:20.663979637Z',
    ]
    stats = cluster_stats(node_names, stat_time_formatted)
    utc_timestamp_average = 1550235205.3
    assert (stats['timestamp'] == pytest.approx(utc_timestamp_average),
            "The timestamp of a cluster has to be the average timestamp of its nodes")


def test_node_timestamps_non_utc():
    node_names = ['node1', 'node2', 'node3']
    stat_time_formatted = [
        "2019-03-01T10:44:58.19881199+01:00",
        "2019-03-01T10:44:55.383089539+01:00",
        "2019-03-01T10:44:51.42243614+01:00",
    ]
    stats = cluster_stats(node_names, stat_time_formatted)
    utc_timestamp_average = 1551429894.7
    assert (stats['timestamp'] == pytest.approx(utc_timestamp_average),
            "The timestamp of a cluster has to be the average timestamp of its nodes")
