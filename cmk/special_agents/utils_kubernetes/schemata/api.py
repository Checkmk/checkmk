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
from typing import Dict, List, Literal, NewType, Optional, Protocol, Sequence, Union

from pydantic import BaseModel
from pydantic.class_validators import validator
from pydantic.fields import Field

Labels = NewType("Labels", Dict[str, str])
PodUID = NewType("PodUID", str)


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


class Deployment(BaseModel):
    metadata: MetaData
    pods: Sequence[PodUID]


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


class PodSpec(BaseModel):
    node: str
    host_network: Optional[str] = None
    dns_policy: Optional[str] = None
    host_ip: Optional[str] = None
    pod_ip: str
    qos_class: Literal["burstable", "besteffort", "guaranteed"]


class ContainerRunningState(BaseModel):
    type: str = Field("running", const=True)
    start_time: int


class ContainerWaitingState(BaseModel):
    type: str = Field("waiting", const=True)
    reason: str
    detail: str


class ContainerTerminatedState(BaseModel):
    type: str = Field("terminated", const=True)
    exit_code: int
    start_time: int
    end_time: int
    reason: Optional[str]
    detail: Optional[str]


class ContainerInfo(BaseModel):
    id: Optional[str]  # id of non-ready container is None
    image: str
    ready: bool
    state: Union[ContainerTerminatedState, ContainerWaitingState, ContainerRunningState]
    restart_count: int


class ConditionType(str, enum.Enum):
    # https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-conditions
    PODSCHEDULED = "scheduled"
    CONTAINERSREADY = "containersready"
    INITIALIZED = "initialized"
    READY = "ready"


class PodCondition(BaseModel):
    status: bool
    type: Optional[ConditionType]
    custom_type: Optional[str]
    reason: Optional[str]
    detail: Optional[str]

    @validator("custom_type")
    @classmethod
    def verify_type(cls, v, values):
        if "type" not in values and not v:
            raise ValueError("either type or custom_type is required")
        return v


class PodStatus(BaseModel):
    conditions: List[PodCondition]
    phase: Phase


class Pod(BaseModel):
    uid: str
    metadata: MetaData
    status: PodStatus
    spec: PodSpec
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

    def deployments(self):
        ...

    def cluster_details(self) -> ClusterInfo:
        ...
