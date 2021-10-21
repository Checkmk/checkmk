#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
This file contains helper functions to convert kubernetes specific
data structures to version independent data structured defined in schemata.api
"""

from __future__ import annotations

import datetime
import time
from collections import defaultdict
from typing import Dict, List, NewType, Optional

from kubernetes import client  # type: ignore[import] # pylint: disable=import-error

from .schemata import api

Labels = NewType("Labels", Dict[str, str])


def parse_frac_prefix(value: str) -> float:
    if value.endswith("m"):
        return 0.001 * float(value[:-1])
    return float(value)


def parse_memory(value: str) -> float:
    if value.endswith("Ki"):
        return 1024 ** 1 * float(value[:-2])
    if value.endswith("Mi"):
        return 1024 ** 2 * float(value[:-2])
    if value.endswith("Gi"):
        return 1024 ** 3 * float(value[:-2])
    if value.endswith("Ti"):
        return 1024 ** 4 * float(value[:-2])
    if value.endswith("Pi"):
        return 1024 ** 5 * float(value[:-2])
    if value.endswith("Ei"):
        return 1024 ** 6 * float(value[:-2])

    if value.endswith("K") or value.endswith("k"):
        return 1e3 * float(value[:-1])
    if value.endswith("M"):
        return 1e6 * float(value[:-1])
    if value.endswith("G"):
        return 1e9 * float(value[:-1])
    if value.endswith("T"):
        return 1e12 * float(value[:-1])
    if value.endswith("P"):
        return 1e15 * float(value[:-1])
    if value.endswith("E"):
        return 1e18 * float(value[:-1])

    # millibytes are a useless, but valid option:
    # https://github.com/kubernetes/kubernetes/issues/28741
    if value.endswith("m"):
        return 1e-3 * float(value[:-1])

    return float(value)


def parse_metadata(metadata: client.V1ObjectMeta, labels=None) -> api.MetaData:
    def convert_to_timestamp(k8s_date_time) -> float:
        if isinstance(k8s_date_time, str):
            date_time = datetime.datetime.strptime(k8s_date_time, "%Y-%m-%dT%H:%M:%SZ")
        elif isinstance(k8s_date_time, datetime.datetime):
            date_time = k8s_date_time
        else:
            raise TypeError(
                f"Can not convert to timestamp: '{k8s_date_time}' of type {type(k8s_date_time)}"
            )
        return time.mktime(date_time.timetuple())

    if not labels:
        labels = metadata.labels if metadata.labels else {}

    return api.MetaData(
        name=metadata.name,
        namespace=metadata.namespace,
        creation_timestamp=convert_to_timestamp(metadata.creation_timestamp),
        labels=labels,
    )


def parse_pod_info(pod: client.V1Pod) -> api.PodInfo:
    info = {}
    if pod.spec:
        info.update({"node": pod.spec.node_name, "host_network": pod.spec.host_network})

    if pod.status:
        info.update(
            {
                "host_ip": pod.status.host_ip,
                "pod_ip": pod.status.pod_ip,
                "qos_class": pod.status.qos_class.lower(),
            }
        )
    return api.PodInfo(**info)


def pod_resources(pod: client.V1Pod) -> api.PodUsageResources:
    memory: Dict[str, float] = defaultdict(float)
    cpu: Dict[str, float] = defaultdict(float)

    for container in pod.spec.containers:
        resources = container.resources
        if not resources:
            continue

        if resources.limits:
            memory["limit"] += parse_memory(resources.limits.get("memory", "inf"))
            cpu["limit"] += parse_frac_prefix(resources.limits.get("cpu", "inf"))
        else:
            memory["limit"] += float("inf")
            cpu["limit"] += float("inf")

        if resources.requests:
            cpu["requests"] += parse_frac_prefix(resources.requests.get("cpu", "0.0"))
            memory["requests"] += parse_memory(resources.requests.get("memory", "0.0"))

    return api.PodUsageResources(cpu=api.Resources(**cpu), memory=api.Resources(**memory))


def pod_containers(pod: client.V1Pod) -> List[api.ContainerInfo]:
    result = []
    for status in pod.status.container_statuses:
        if status.state.terminated is not None:
            state = api.ContainerState.TERMINATED
        elif status.state.running is not None:
            state = api.ContainerState.RUNNING
        elif status.state.waiting is not None:
            state = api.ContainerState.WAITING
        else:
            raise AssertionError("Unknown contianer state {status.state}")

        result.append(api.ContainerInfo(id=status.container_id, image=status.image, state=state))
    return result


class NodeLabels:
    def __init__(self, labels: Optional[Labels]) -> None:
        self._labels: Labels = Labels({})
        if labels is not None:
            self._labels = labels
        self._is_control_plane = (
            # 1.18 returns an empty string, 1.20 returns 'true'
            "node-role.kubernetes.io/master" in self._labels
            or "node-role.kubernetes.io/control-plane" in self._labels
        )

    @property
    def is_control_plane(self) -> bool:
        return self._is_control_plane

    def to_cmk_labels(self) -> api.Labels:
        """Parse node labels

        >>> NodeLabels(Labels({'node-role.kubernetes.io/master': 'yes'})).to_cmk_labels()
        {'node-role.kubernetes.io/master': 'yes', 'cmk/kubernetes_object': 'control-plane_node', 'cmk/kubernetes': 'yes'}

        """
        labels = self._labels.copy()
        labels["cmk/kubernetes_object"] = (
            "control-plane_node" if self._is_control_plane else "worker_node"
        )
        labels["cmk/kubernetes"] = "yes"
        return api.Labels(labels)


def node_conditions(node: client.V1Node) -> Optional[api.NodeStatus]:
    if not node.status:
        return None
    conditions = node.status.conditions
    if not conditions:
        return None
    return api.NodeStatus(**{c.type: bool(c.status) for c in conditions})


def parse_node_resources(node: client.V1Node) -> Dict[str, api.NodeResources]:
    if node.status:
        capacity = node.status.capacity
        allocatable = node.status.allocatable
    else:
        capacity, allocatable = None, None

    return node_resources(capacity, allocatable)


def node_resources(capacity, allocatable) -> Dict[str, api.NodeResources]:
    resources = {
        "capacity": api.NodeResources(),
        "allocatable": api.NodeResources(),
    }

    if not capacity and not allocatable:
        return resources

    if capacity:
        resources["capacity"] = api.NodeResources(
            cpu=parse_frac_prefix(capacity.get("cpu", 0.0)),
            memory=parse_memory(capacity.get("memory", 0.0)),
            pods=capacity.get("pods", 0),
        )
    if allocatable:
        resources["allocatable"] = api.NodeResources(
            cpu=parse_frac_prefix(allocatable.get("cpu", 0.0)),
            memory=parse_memory(allocatable.get("memory", 0.0)),
            pods=allocatable.get("pods", 0),
        )
    return resources


def pod_from_client(pod: client.V1Pod) -> api.Pod:
    return api.Pod(
        uid=pod.metadata.uid,
        metadata=parse_metadata(pod.metadata),
        phase=api.Phase(pod.status.phase.lower()),
        info=parse_pod_info(pod),
        resources=pod_resources(pod),
        containers=pod_containers(pod),
    )


def node_from_client(node: client.V1Node) -> api.Node:
    node_labels = NodeLabels(node.metadata.labels)
    labels = node_labels.to_cmk_labels()
    return api.Node(
        metadata=parse_metadata(node.metadata, labels=labels),
        conditions=node_conditions(node),
        resources=parse_node_resources(node),
        control_plane=node_labels.is_control_plane,
    )
