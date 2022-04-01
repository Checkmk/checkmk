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

CronJobUID = NewType("CronJobUID", str)
JobUID = NewType("JobUID", str)
PodUID = NewType("PodUID", str)
LabelName = NewType("LabelName", str)
LabelValue = NewType("LabelValue", str)
GitVersion = NewType("GitVersion", str)


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
IpAddress = NewType("IpAddress", str)


class MetaData(BaseModel):
    name: str
    namespace: Optional[Namespace] = None
    creation_timestamp: Optional[CreationTimestamp] = None
    labels: Optional[Labels] = None


class NodeMetaData(MetaData):
    creation_timestamp: CreationTimestamp
    labels: Labels


class PodMetaData(MetaData):
    namespace: Namespace


class NodeConditionStatus(str, enum.Enum):
    TRUE = "True"
    FALSE = "False"
    UNKNOWN = "Unknown"


class NodeCondition(BaseModel):
    status: NodeConditionStatus
    type_: str
    reason: Optional[str]
    detail: Optional[str]
    last_transition_time: Optional[int]


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
    proxy_version: str
    health: HealthZ


class NodeInfo(BaseModel):
    architecture: str
    kernel_version: str
    os_image: str
    operating_system: str
    container_runtime_version: str


class NodeAddress(BaseModel):
    address: IpAddress
    # according to the docs type_ is "Hostname", "ExternalIP", "InternalIP", but we also saw
    # "InternalDNS" and "ExternalDNS" on an eks cluster
    type_: str


NodeAddresses = Sequence[NodeAddress]


class NodeStatus(BaseModel):
    conditions: Optional[Sequence[NodeCondition]]
    node_info: NodeInfo
    addresses: NodeAddresses


class Node(BaseModel):
    metadata: NodeMetaData
    status: NodeStatus
    roles: Sequence[str]
    resources: Dict[str, NodeResources]
    kubelet_info: KubeletInfo


class Replicas(BaseModel):
    replicas: int
    updated: int
    available: int
    ready: int
    unavailable: int


class ConditionStatus(str, enum.Enum):
    TRUE = "True"
    FALSE = "False"
    UNKNOWN = "Unknown"


class DeploymentCondition(BaseModel):
    status: ConditionStatus
    last_transition_time: float
    reason: str
    message: str


class DeploymentStatus(BaseModel):
    # https://v1-18.docs.kubernetes.io/docs/reference/generated/kubernetes-api/v1.18/#deploymentstatus-v1-apps
    replicas: Replicas
    conditions: Mapping[str, DeploymentCondition]


class MatchExpression(BaseModel):
    key: LabelName
    operator: Literal["In", "NotIn", "Exists", "DoesNotExist"]
    values: Sequence[LabelValue]


MatchLabels = Mapping[LabelName, LabelValue]
MatchExpressions = Sequence[MatchExpression]


class Selector(BaseModel):
    match_labels: MatchLabels
    match_expressions: MatchExpressions


class RollingUpdate(BaseModel):
    type_: Literal["RollingUpdate"] = Field("RollingUpdate", const=True)
    max_surge: str
    max_unavailable: str


class StatefulSetRollingUpdate(BaseModel):
    type_: Literal["RollingUpdate"] = Field("RollingUpdate", const=True)
    partition: int


class Recreate(BaseModel):
    type_: Literal["Recreate"] = Field("Recreate", const=True)


class OnDelete(BaseModel):
    type_: Literal["OnDelete"] = Field("OnDelete", const=True)


class DeploymentSpec(BaseModel):
    strategy: Union[Recreate, RollingUpdate] = Field(discriminator="type_")
    selector: Selector


class Deployment(BaseModel):
    metadata: MetaData
    spec: DeploymentSpec
    status: DeploymentStatus
    pods: Sequence[PodUID]


class DaemonSetSpec(BaseModel):
    strategy: Union[OnDelete, RollingUpdate] = Field(discriminator="type_")
    selector: Selector


class DaemonSet(BaseModel):
    metadata: MetaData
    spec: DaemonSetSpec
    pods: Sequence[PodUID]


class StatefulSetSpec(BaseModel):
    strategy: Union[OnDelete, StatefulSetRollingUpdate] = Field(discriminator="type_")
    selector: Selector


class StatefulSet(BaseModel):
    metadata: MetaData
    spec: StatefulSetSpec
    pods: Sequence[PodUID]


class Phase(str, enum.Enum):
    RUNNING = "running"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class ResourcesRequirements(BaseModel):
    memory: Optional[float] = None
    cpu: Optional[float] = None


class ContainerResources(BaseModel):
    limits: ResourcesRequirements
    requests: ResourcesRequirements


ImagePullPolicy = Literal["Always", "Never", "IfNotPresent"]


class ContainerSpec(BaseModel):
    resources: ContainerResources
    name: str
    image_pull_policy: ImagePullPolicy


class PodSpec(BaseModel):
    node: Optional[NodeName] = None
    host_network: Optional[str] = None
    dns_policy: Optional[str] = None
    restart_policy: RestartPolicy
    containers: Sequence[ContainerSpec]
    init_containers: Sequence[ContainerSpec]


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


ContainerState = Union[ContainerTerminatedState, ContainerWaitingState, ContainerRunningState]


class ContainerStatus(BaseModel):
    container_id: Optional[str]  # container_id of non-ready container is None
    image_id: str  # image_id of non-ready container is ""
    name: str
    image: str
    ready: bool
    state: ContainerState
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
    start_time: Optional[Timestamp]  # None if pod is faulty
    host_ip: Optional[IpAddress] = None
    pod_ip: Optional[IpAddress] = None
    qos_class: QosClass


class Pod(BaseModel):
    uid: PodUID
    metadata: PodMetaData
    status: PodStatus
    spec: PodSpec
    containers: Mapping[str, ContainerStatus]
    init_containers: Mapping[str, ContainerStatus]


class ConcurrencyPolicy(enum.Enum):
    # specifies how to treat concurrent executions of a Job.
    Allow = "Allow"  # allows concurrently running jobs
    Forbid = "Forbid"  # does not allow concurrent runs
    Replace = "Replace"  # replaces the currently running job


class CronJobSpec(BaseModel):
    concurrency_policy: ConcurrencyPolicy
    schedule: str


class CronJob(BaseModel):
    uid: CronJobUID
    metadata: MetaData
    spec: CronJobSpec
    pod_uids: Sequence[PodUID]


class ClusterDetails(BaseModel):
    """section: kube_cluster_details_v1"""

    api_health: APIHealth
    version: GitVersion


class API(Protocol):
    def cron_jobs(self) -> Sequence[CronJob]:
        ...

    def nodes(self) -> Sequence[Node]:
        ...

    def pods(self) -> Sequence[Pod]:
        ...

    def deployments(self):
        ...

    def daemon_sets(self):
        ...

    def statefulsets(self):
        ...

    def cluster_details(self) -> ClusterDetails:
        ...
