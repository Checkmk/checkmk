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
from typing import Dict, List, Literal, Mapping, NewType, Optional, Protocol, Sequence, Union

from pydantic import BaseModel
from pydantic.class_validators import validator
from pydantic.fields import Field

PodUID = NewType("PodUID", str)
LabelName = NewType("LabelName", str)
LabelValue = NewType("LabelValue", str)


class Label(BaseModel):
    name: LabelName
    value: LabelValue


Labels = Mapping[LabelName, Label]
Timestamp = NewType("Timestamp", float)

# This information is from the one-page API overview v1.22
# Restart policy for all containers within the pod. Default to Always. More info:
RestartPolicy = Literal["Always", "OnFailure", "Never"]

# This information is from the one-page API overview v1.22
# The Quality of Service (QOS) classification assigned to the pod based on resource requirements.
QosClass = Literal["burstable", "besteffort", "guaranteed"]

CreationTimestamp = NewType("CreationTimestamp", float)
Namespace = NewType("Namespace", str)
NodeName = NewType("NodeName", str)


class MetaData(BaseModel):
    name: str
    namespace: Optional[Namespace] = None
    creation_timestamp: Optional[CreationTimestamp] = None
    labels: Optional[Labels] = None
    prefix = ""
    use_namespace = False


class NodeConditions(BaseModel):
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
    """section: kube_node_kubelet_v1"""

    version: str
    health: HealthZ


class NodeInfo(BaseModel):
    architecture: str
    kernel_version: str
    os_image: str


class NodeStatus(BaseModel):
    conditions: NodeConditions
    node_info: NodeInfo


class Node(BaseModel):
    metadata: MetaData
    status: NodeStatus
    control_plane: bool
    resources: Dict[str, NodeResources]
    kubelet_info: KubeletInfo


class DeploymentReplicas(BaseModel):
    updated: int
    available: int
    ready: int
    unavailable: int


class ConditionStatus(str, enum.Enum):
    TRUE = "True"
    FALSE = "False"
    UNKNOWN = "Unknown"


class DeploymentCondition(BaseModel):
    type_: str
    status: ConditionStatus
    last_transition_time: float
    reason: str
    message: str


class DeploymentStatus(BaseModel):
    # https://v1-18.docs.kubernetes.io/docs/reference/generated/kubernetes-api/v1.18/#deploymentstatus-v1-apps
    replicas: DeploymentReplicas
    conditions: Sequence[DeploymentCondition]


class Deployment(BaseModel):
    metadata: MetaData
    status: DeploymentStatus
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
    node: Optional[NodeName] = None
    host_network: Optional[str] = None
    dns_policy: Optional[str] = None
    host_ip: Optional[str] = None
    pod_ip: Optional[str] = None
    qos_class: QosClass


class ContainerRunningState(BaseModel):
    type: str = Field("running", const=True)
    start_time: int


class ContainerWaitingState(BaseModel):
    type: str = Field("waiting", const=True)
    reason: str
    detail: Optional[str]


class ContainerTerminatedState(BaseModel):
    type: str = Field("terminated", const=True)
    exit_code: int
    start_time: int
    end_time: int
    reason: Optional[str]
    detail: Optional[str]


class ContainerInfo(BaseModel):
    id: Optional[str]  # id of non-ready container is None
    name: str
    image: str
    ready: bool
    state: Union[ContainerTerminatedState, ContainerWaitingState, ContainerRunningState]
    restart_count: int


class StartTime(BaseModel):
    """section: kube_start_time_v1"""

    start_time: int


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
    last_transition_time: Optional[int]

    @validator("custom_type")
    @classmethod
    def verify_type(cls, v, values):
        if "type" not in values and not v:
            raise ValueError("either type or custom_type is required")
        return v


class PodStatus(BaseModel):
    conditions: List[PodCondition]
    phase: Phase
    start_time: Optional[int]  # None if pod is faulty


class Pod(BaseModel):
    uid: str
    metadata: MetaData
    status: PodStatus
    spec: PodSpec
    resources: PodUsageResources
    containers: Mapping[str, ContainerInfo]


class ClusterInfo(BaseModel):
    """section: kube_cluster_details_v1"""

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
