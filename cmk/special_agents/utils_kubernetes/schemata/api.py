#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
The schemas contained in this file define the stable API between kubernetes and
the special agent.
The schemas should not be affected by different kubernetes server or client versions.

This file should not contain any code and should not import from anywhere
except the python standard library or pydantic.
"""

import enum
from typing import Dict, List, Literal, NewType, Optional, Protocol, Sequence

from pydantic import BaseModel

Labels = NewType("Labels", Dict[str, str])


class MetaData(BaseModel):
    name: str
    namespace: Optional[str] = None
    creation_timestamp: Optional[float] = None
    labels: Optional[Labels] = None
    prefix = ""
    use_namespace = False


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


class HealthZ(BaseModel):
    status_code: int
    response: str
    # only set if status_code != 200
    verbose_response: Optional[str]


class APIHealth(BaseModel):
    ready: HealthZ
    live: HealthZ


class KubeletInfo(BaseModel):
    """section: k8s_node_kubelet_v1"""

    version: str
    health: HealthZ


class Node(BaseModel):
    metadata: MetaData
    conditions: NodeStatus
    control_plane: bool
    resources: Dict[str, NodeResources]
    kubelet_info: KubeletInfo


class Resources(BaseModel):
    limit: float = float("inf")
    requests: float = 0.0


class Phase(str, enum.Enum):
    RUNNING = "running"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown "


class PodUsageResources(BaseModel):
    cpu: Resources
    memory: Resources


class PodInfo(BaseModel):
    node: str
    host_network: Optional[str] = None
    dns_policy: Optional[str] = None
    host_ip: Optional[str] = None
    pod_ip: str
    qos_class: Literal["burstable", "besteffort", "guaranteed"]


class ContainerState(str, enum.Enum):
    # https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#container-states
    RUNNING = "running"
    WAITING = "waiting"
    TERMINATED = "terminated"


class ContainerInfo(BaseModel):
    image: str
    state: ContainerState


class Pod(BaseModel):
    uid: str
    metadata: MetaData
    phase: Phase
    info: PodInfo
    resources: PodUsageResources
    containers: List[ContainerInfo]


class ClusterInfo(BaseModel):
    """section: k8s_cluster_details_v1"""

    api_health: APIHealth


class API(Protocol):
    def nodes(self) -> Sequence[Node]:
        ...

    def pods(self) -> Sequence[Pod]:
        ...

    def cluster_details(self) -> ClusterInfo:
        ...
