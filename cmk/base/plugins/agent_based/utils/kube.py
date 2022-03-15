#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from typing import Literal, Mapping, NewType, Optional, Sequence, Tuple, TypedDict, Union

from pydantic import BaseModel, Field

from cmk.base.plugins.agent_based.agent_based_api.v1 import HostLabel
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import HostLabelGenerator

LabelName = NewType("LabelName", str)
LabelValue = NewType("LabelValue", str)


class Label(BaseModel):
    name: LabelName
    value: LabelValue


ContainerName = NewType("ContainerName", str)
Labels = Mapping[LabelName, Label]
CreationTimestamp = NewType("CreationTimestamp", float)
HostName = NewType("HostName", str)
IpAddress = NewType("IpAddress", str)
Namespace = NewType("Namespace", str)
NodeName = NewType("NodeName", str)
OsName = NewType("OsName", str)
PodUID = NewType("PodUID", str)
PodSequence = Sequence[str]
PythonCompiler = NewType("PythonCompiler", str)
Timestamp = NewType("Timestamp", float)
Version = NewType("Version", str)


# This information is from the one-page API overview v1.22
# Restart policy for all containers within the pod. Default to Always. More info:
RestartPolicy = Literal["Always", "OnFailure", "Never"]


# This information is from the one-page API overview v1.22
# The Quality of Service (QOS) classification assigned to the pod based on resource requirements.
QosClass = Literal["burstable", "besteffort", "guaranteed"]


class ControllerType(enum.Enum):
    deployment = "deployment"
    daemon_set = "daemon_set"
    statefulset = "statefulset"

    @staticmethod
    def from_str(label):
        if label == "deployment":
            return ControllerType.deployment
        if label == "daemon_set":
            return ControllerType.daemon_set
        if label == "statefulset":
            return ControllerType.statefulset
        raise ValueError(f"Unknown controller type: {label}")


class Controller(BaseModel):
    type_: ControllerType
    name: str


# A sequence of controllers, e.g. deployment -> replica set. For two adjacent elements, the first
# one controls the second one. The final element controls the pod (but this is not implemented yet).
# Control chains may be incomplete.
ControlChain = Sequence[Controller]


def condition_short_description(name: str, status: str) -> str:
    return f"{name.upper()}: {status}"


def condition_detailed_description(
    name: str,
    status: str,
    reason: Optional[str],
    message: Optional[str],
) -> str:
    """Format the condition for Result summary or details

    Examples:
        >>> condition_detailed_description("Ready", "False", "Waiting", "ContainerCreating")
        'READY: False (Waiting: ContainerCreating)'

    """
    return f"{condition_short_description(name, status)} ({reason}: {message})"


def kube_labels_to_cmk_labels(labels: Labels) -> HostLabelGenerator:
    for label in labels.values():
        if (value := label.value) == "":
            value = LabelValue("true")
        yield HostLabel(label.name, value)


class KubernetesError(Exception):
    pass


class CollectorState(enum.Enum):
    OK = "ok"
    ERROR = "error"


class CollectorHandlerLog(BaseModel):
    status: CollectorState
    title: str
    detail: Optional[str]


class PlatformMetadata(BaseModel):
    os_name: OsName
    os_version: Version
    python_version: Version
    python_compiler: PythonCompiler


class CheckmkKubeAgentMetadata(BaseModel):
    project_version: Version


class CollectorMetadata(BaseModel):
    node: NodeName
    host_name: HostName  # This looks like the pod name, but it is not. It is
    # possible to give the host an arbitrary host name, different from the pod
    # name which is managed by Kubernetes.
    container_platform: PlatformMetadata
    checkmk_kube_agent: CheckmkKubeAgentMetadata


class ClusterCollectorMetadata(CollectorMetadata):
    pass


class CollectorType(enum.Enum):
    CONTAINER_METRICS = "Container Metrics"
    MACHINE_SECTIONS = "Machine Sections"


class Components(BaseModel):
    cadvisor_version: Optional[Version]
    checkmk_agent_version: Optional[Version]


class NodeComponent(BaseModel):
    collector_type: CollectorType
    checkmk_kube_agent: CheckmkKubeAgentMetadata
    name: str
    version: Version


class NodeMetadata(BaseModel):
    name: NodeName
    components: Mapping[str, NodeComponent]


class CollectorComponentsMetadata(BaseModel):
    """section: kube_collector_metadata_v1"""

    processing_log: CollectorHandlerLog
    cluster_collector: Optional[ClusterCollectorMetadata]
    nodes: Optional[Sequence[NodeMetadata]]


class CollectorProcessingLogs(BaseModel):
    """section: kube_collector_processing_logs_v1"""

    container: CollectorHandlerLog
    machine: CollectorHandlerLog


class Phase(str, enum.Enum):
    RUNNING = "running"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class PodLifeCycle(BaseModel):
    """section: kube_pod_lifecycle_v1"""

    phase: Phase


class ReadyCount(BaseModel):
    ready: int = 0
    not_ready: int = 0

    @property
    def total(self) -> int:
        return self.ready + self.not_ready


class NodeConditionStatus(str, enum.Enum):
    TRUE = "True"
    FALSE = "False"
    UNKNOWN = "Unknown"


class NodeCount(BaseModel):
    """section: kube_node_count_v1"""

    worker: ReadyCount = ReadyCount()
    control_plane: ReadyCount = ReadyCount()


class NodeCondition(BaseModel):
    status: NodeConditionStatus
    reason: Optional[str]
    detail: Optional[str]
    last_transition_time: Optional[int]


class TruthyNodeCondition(NodeCondition):
    """TruthyNodeCondition has an "OK" state when its status is True"""

    def is_ok(self) -> bool:
        return self.status == NodeConditionStatus.TRUE


class FalsyNodeCondition(NodeCondition):
    """FalsyNodeCondition has an "OK" state when its status is False"""

    def is_ok(self) -> bool:
        return self.status == NodeConditionStatus.FALSE


class FalsyNodeCustomCondition(FalsyNodeCondition):
    """FalsyNodeCustomCondition mainly come from Node Problem Detector.
    Its type can be user-defined, hence it being a string."""

    type_: str


class NodeConditions(BaseModel):
    """section: k8s_node_conditions_v1"""

    ready: TruthyNodeCondition
    memorypressure: FalsyNodeCondition
    diskpressure: FalsyNodeCondition
    pidpressure: FalsyNodeCondition
    networkunavailable: Optional[FalsyNodeCondition]


class NodeCustomConditions(BaseModel):
    """section: k8s_node_custom_conditions_v1"""

    custom_conditions: Sequence[FalsyNodeCustomCondition]


class ConditionStatus(str, enum.Enum):
    TRUE = "True"
    FALSE = "False"
    UNKNOWN = "Unknown"


class DeploymentCondition(BaseModel):
    status: ConditionStatus
    last_transition_time: float
    reason: str
    message: str


class DeploymentConditions(BaseModel):
    """section: kube_deployment_conditions_v1"""

    available: Optional[DeploymentCondition]
    progressing: Optional[DeploymentCondition]
    replicafailure: Optional[DeploymentCondition]


class ClusterInfo(BaseModel):
    """section: kube_cluster_info_v1"""

    name: str


VSResultAge = Union[Tuple[Literal["levels"], Tuple[int, int]], Literal["no_levels"]]


class NodeAddress(BaseModel):
    address: IpAddress
    # according to the docs type_ is "Hostname", "ExternalIP", "InternalIP", but we also saw
    # "InternalDNS" and "ExternalDNS" on an eks cluster
    type_: str


NodeAddresses = Sequence[NodeAddress]


class NodeInfo(BaseModel):
    """section: kube_node_info_v1"""

    architecture: str
    kernel_version: str
    os_image: str
    operating_system: str
    container_runtime_version: str
    name: NodeName
    creation_timestamp: CreationTimestamp
    labels: Labels
    addresses: NodeAddresses
    cluster: str


class HealthZ(BaseModel):
    status_code: int
    response: str
    # only set if status_code != 200
    verbose_response: Optional[str]


class KubeletInfo(BaseModel):
    """section: kube_node_kubelet_v1"""

    version: str
    proxy_version: str
    health: HealthZ


class APIHealth(BaseModel):
    ready: HealthZ
    live: HealthZ


class PodInfo(BaseModel):
    """section: kube_pod_info_v1"""

    namespace: Optional[Namespace]
    name: str
    creation_timestamp: Optional[CreationTimestamp]
    labels: Labels  # used for host labels
    node: Optional[NodeName]  # this is optional, because there may be pods, which are not
    # scheduled on any node (e.g., no node with enough capacity is available).
    host_network: Optional[str]
    dns_policy: Optional[str]
    host_ip: Optional[IpAddress]
    pod_ip: Optional[IpAddress]
    qos_class: QosClass
    restart_policy: RestartPolicy
    uid: PodUID
    # TODO: see CMK-9901
    controllers: ControlChain = []
    cluster: str


class ClusterDetails(BaseModel):
    """section: kube_cluster_details_v1"""

    api_health: APIHealth


class PodResources(BaseModel):
    """section: kube_pod_resources_v1"""

    running: PodSequence = []
    pending: PodSequence = []
    succeeded: PodSequence = []
    failed: PodSequence = []
    unknown: PodSequence = []


class AllocatablePods(BaseModel):
    """section: kube_allocatable_pods_v1"""

    capacity: int
    allocatable: int


class ContainerCount(BaseModel):
    """section: kube_node_container_count_v1"""

    running: int = 0
    waiting: int = 0
    terminated: int = 0


class Memory(BaseModel):
    type_: Literal["memory"] = Field("memory", const=True)
    usage: float


class Cpu(BaseModel):
    type_: Literal["cpu"] = Field("cpu", const=True)
    usage: float


class PerformanceUsage(BaseModel):
    """section: [kube_performance_cpu_v1, kube_performance_memory_v1]"""

    resource: Union[Cpu, Memory] = Field(discriminator="type_")


class StartTime(BaseModel):
    """section: kube_start_time_v1"""

    start_time: int


class PodCondition(BaseModel):
    status: bool
    reason: Optional[str]
    detail: Optional[str]
    last_transition_time: Optional[int]


class PodConditions(BaseModel):
    """section: kube_pod_conditions_v1"""

    initialized: Optional[PodCondition]
    scheduled: PodCondition
    containersready: Optional[PodCondition]
    ready: Optional[PodCondition]


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


class ContainerStatus(BaseModel):
    container_id: Optional[str]  # container_id of non-ready container is None
    image_id: str  # image_id of non-ready container is ""
    name: str
    image: str
    ready: bool
    state: Union[ContainerTerminatedState, ContainerWaitingState, ContainerRunningState]
    restart_count: int


ImagePullPolicy = Literal["Always", "Never", "IfNotPresent"]


class ContainerSpec(BaseModel):
    image_pull_policy: ImagePullPolicy


class ContainerSpecs(BaseModel):
    """section: kube_pod_container_specs_v1"""

    containers: Mapping[ContainerName, ContainerSpec]


class ThinContainers(BaseModel):
    """ThinContainers reduces agent ouput duplication.

    Container information is often times duplicated across different piggyback hosts. In order
    to reduce the amount of duplication, we maintain this data structure, which is based on a smaller
    subset of fields. This structure can then be used with hosts such as Deployment, which only
    require a small amount of container-related information.
    """

    images: frozenset[str]
    names: Sequence[str]


class MatchExpression(TypedDict):
    key: LabelName
    operator: Literal["In", "NotIn", "Exists", "DoesNotExist"]
    values: Sequence[LabelValue]


MatchLabels = Mapping[LabelName, LabelValue]
MatchExpressions = Sequence[MatchExpression]


class Selector(BaseModel):
    match_labels: MatchLabels
    match_expressions: MatchExpressions


class DeploymentInfo(BaseModel):
    """section: kube_deployment_info_v1"""

    name: str
    namespace: Namespace
    labels: Labels
    selector: Selector
    creation_timestamp: CreationTimestamp
    containers: ThinContainers
    cluster: str


class DaemonSetInfo(BaseModel):
    """section: kube_daemonset_info_v1"""

    name: str
    namespace: Namespace
    labels: Labels
    selector: Selector
    creation_timestamp: CreationTimestamp
    cluster: str


class StatefulSetInfo(BaseModel):
    """section: kube_statefulset_info_v1"""

    name: str
    namespace: Namespace
    labels: Labels
    selector: Selector
    creation_timestamp: CreationTimestamp
    cluster: str


class PodContainers(BaseModel):
    """section: kube_pod_containers_v1"""

    containers: Mapping[str, ContainerStatus]


class Replicas(BaseModel):
    replicas: int
    updated: int
    available: int
    ready: int
    unavailable: int


class RollingUpdate(BaseModel):
    type_: Literal["RollingUpdate"] = Field("RollingUpdate", const=True)
    max_surge: str
    max_unavailable: str


class Recreate(BaseModel):
    type_: Literal["Recreate"] = Field("Recreate", const=True)


class OnDelete(BaseModel):
    type_: Literal["OnDelete"] = Field("OnDelete", const=True)


class DeploymentStrategy(BaseModel):
    """section: kube_deployment_strategy_v1"""

    strategy: Union[Recreate, RollingUpdate] = Field(discriminator="type_")


class DaemonSetStrategy(BaseModel):
    """section: kube_daemonset_strategy_v1"""

    strategy: Union[OnDelete, RollingUpdate] = Field(discriminator="type_")


class StatefulSetRollingUpdate(BaseModel):
    type_: Literal["RollingUpdate"] = Field("RollingUpdate", const=True)
    partition: int


class StatefulSetStrategy(BaseModel):
    """section: kube_statefulset_strategy_v1"""

    strategy: Union[OnDelete, StatefulSetRollingUpdate] = Field(discriminator="type_")
