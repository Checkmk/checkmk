#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import datetime
import enum
import time
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
    def convert_to_timestamp(date_time) -> float:
        return time.mktime(datetime.datetime.strptime(date_time, "%Y-%m-%dT%H:%M:%SZ").timetuple())

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


class PodResources(BaseModel):
    cpu: float = float("inf")
    memory: float = float("inf")


class Phase(str, enum.Enum):
    RUNNING = "running"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown "


class PodAPI(BaseModel):
    metadata: MetaData
    phase: Phase
    info: PodInfo

    @classmethod
    def from_client(cls, pod: client.V1Pod) -> PodAPI:
        return cls(
            metadata=parse_metadata(pod.metadata),
            phase=Phase(pod.status.phase.lower()),
            info=parse_pod_info(pod),
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


class NodeAPI(BaseModel):
    metadata: MetaData
    conditions: NodeStatus
    resources: Dict[str, NodeResources]

    @classmethod
    def from_client(cls, node: client.V1Node):
        labels = node_labels(Labels(node.metadata.labels))
        return cls(
            metadata=parse_metadata(node.metadata, labels=labels),
            conditions=node_conditions(node),
            resources=parse_node_resources(node),
        )


def node_labels(labels: Labels) -> Labels:
    """Parse node labels

    >>> node_labels(Labels({'node-role.kubernetes.io/master': 'yes'}))
    {'node-role.kubernetes.io/master': 'yes', 'cmk/kubernetes_object': 'control-plane_node', 'cmk/kubernetes': 'yes'}

    """

    is_control_plane = (
        # 1.18 returns an empty string, 1.20 returns 'true'
        ("node-role.kubernetes.io/control-plane" in labels)
        or ("node-role.kubernetes.io/master" in labels)
    )

    labels["cmk/kubernetes_object"] = "control-plane_node" if is_control_plane else "worker_node"
    labels["cmk/kubernetes"] = "yes"
    return labels


def node_conditions(node: client.V1Node) -> Optional[NodeStatus]:
    if not node.status:
        return None
    conditions = node.status.conditions
    if not conditions:
        return None
    return NodeStatus(**{c.type: c.status for c in conditions})


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
