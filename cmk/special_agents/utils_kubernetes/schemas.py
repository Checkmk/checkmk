#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import datetime
import enum
import time
from collections import defaultdict
from typing import Dict, NewType, Optional

from kubernetes import client  # type: ignore[import] # pylint: disable=import-error
from pydantic import BaseModel
from typing_extensions import Literal

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


def parse_metadata(metadata: client.V1ObjectMeta, labels=None) -> MetaData:
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

    return MetaData(
        name=metadata.name,
        namespace=metadata.namespace,
        creation_timestamp=convert_to_timestamp(metadata.creation_timestamp),
        labels=labels,
    )


class MetaData(BaseModel):
    name: str
    namespace: Optional[str] = None
    creation_timestamp: Optional[float] = None
    labels: Optional[Labels] = None
    prefix = ""
    use_namespace = False


class NamespaceConfig(BaseModel):
    metadata: MetaData
    phase: Optional[str] = None


class PodInfo(BaseModel):
    node: str
    host_network: Optional[str] = None
    dns_policy: Optional[str] = None
    host_ip: Optional[str] = None
    pod_ip: str
    qos_class: Literal["burstable", "besteffort", "guaranteed"]


def parse_pod_info(pod: client.V1Pod) -> PodInfo:
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
    return PodInfo(**info)


class Resources(BaseModel):
    limit: float = float("inf")
    requests: float = 0.0


class PodUsageResources(BaseModel):
    cpu: Resources
    memory: Resources


def pod_resources(pod: client.V1Pod) -> PodUsageResources:
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

    return PodUsageResources(cpu=Resources(**cpu), memory=Resources(**memory))


class Phase(str, enum.Enum):
    RUNNING = "running"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown "


class PodAPI(BaseModel):
    uid: str
    metadata: MetaData
    phase: Phase
    info: PodInfo
    resources: PodUsageResources

    @classmethod
    def from_client(cls, pod: client.V1Pod) -> PodAPI:
        return cls(
            uid=pod.metadata.uid,
            metadata=parse_metadata(pod.metadata),
            phase=Phase(pod.status.phase.lower()),
            info=parse_pod_info(pod),
            resources=pod_resources(pod),
        )


class NodeStatus(BaseModel):
    NetworkUnavailable: Optional[bool] = None
    MemoryPressure: bool
    DiskPressure: bool
    PIDPressure: bool
    Ready: bool


class NodeResources(BaseModel):
    cpu = 0.0
    memory = 0.0
    pods = 0


class APIHealthStatus(BaseModel):
    status_code: int
    response: str
    # only set if status_code != 200
    verbose_response: Optional[str]


class APIHealth(BaseModel):
    ready: APIHealthStatus
    live: APIHealthStatus


class ClusterInfo(BaseModel):
    """section: k8s_cluster_details_v1"""

    api_health: APIHealth


class NodeAPI(BaseModel):
    metadata: MetaData
    conditions: NodeStatus
    control_plane: bool
    resources: Dict[str, NodeResources]

    @classmethod
    def from_client(cls, node: client.V1Node) -> NodeAPI:
        node_labels = NodeLabels(node.metadata.labels)
        return cls(
            metadata=parse_metadata(node.metadata, labels=node_labels.to_cmk_labels()),
            conditions=node_conditions(node),
            resources=parse_node_resources(node),
            control_plane=node_labels.is_control_plane,
        )


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

    def to_cmk_labels(self) -> Labels:
        """Parse node labels

        >>> NodeLabels(Labels({'node-role.kubernetes.io/master': 'yes'})).to_cmk_labels()
        {'node-role.kubernetes.io/master': 'yes', 'cmk/kubernetes_object': 'control-plane_node', 'cmk/kubernetes': 'yes'}

        """
        labels = self._labels.copy()
        labels["cmk/kubernetes_object"] = (
            "control-plane_node" if self._is_control_plane else "worker_node"
        )
        labels["cmk/kubernetes"] = "yes"
        return Labels(labels)


def node_conditions(node: client.V1Node) -> Optional[NodeStatus]:
    if not node.status:
        return None
    conditions = node.status.conditions
    if not conditions:
        return None
    return NodeStatus(**{c.type: bool(c.status) for c in conditions})


def parse_node_resources(node: client.V1Node) -> Dict[str, NodeResources]:
    if node.status:
        capacity = node.status.capacity
        allocatable = node.status.allocatable
    else:
        capacity, allocatable = None, None

    return node_resources(capacity, allocatable)


def node_resources(capacity, allocatable) -> Dict[str, NodeResources]:
    resources = {
        "capacity": NodeResources(),
        "allocatable": NodeResources(),
    }

    if not capacity and not allocatable:
        return resources

    if capacity:
        resources["capacity"] = NodeResources(
            cpu=parse_frac_prefix(capacity.get("cpu", 0.0)),
            memory=parse_memory(capacity.get("memory", 0.0)),
            pods=capacity.get("pods", 0),
        )
    if allocatable:
        resources["allocatable"] = NodeResources(
            cpu=parse_frac_prefix(allocatable.get("cpu", 0.0)),
            memory=parse_memory(allocatable.get("memory", 0.0)),
            pods=allocatable.get("pods", 0),
        )
    return resources
