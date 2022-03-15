#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
The schemas contained in this file are used to serialize data in the agent output.

This file should not contain any code and should not import from anywhere
except the python standard library or pydantic.
"""

import enum
from typing import Literal, Mapping, NewType, Optional, Sequence, Union

from pydantic import BaseModel, Field

from cmk.special_agents.utils_kubernetes.schemata import api

ContainerName = NewType("ContainerName", str)
HostName = NewType("HostName", str)
PodSequence = Sequence[str]
NodeName = NewType("NodeName", str)
OsName = NewType("OsName", str)
PythonCompiler = NewType("PythonCompiler", str)
Timestamp = NewType("Timestamp", float)
Version = NewType("Version", str)


class PerformanceMetric(BaseModel):
    value: float
    timestamp: float


class PerformanceContainer(BaseModel):
    name: ContainerName


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


class NodeCollectorMetadata(CollectorMetadata):
    collector_type: CollectorType
    components: Components


class Metadata(BaseModel):
    cluster_collector_metadata: ClusterCollectorMetadata
    node_collector_metadata: Sequence[NodeCollectorMetadata]


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


class Resources(BaseModel):
    """sections: "[kube_memory_resources_v1, kube_cpu_resources_v1]"""

    request: float
    limit: float
    count_unspecified_requests: int
    count_unspecified_limits: int
    count_zeroed_limits: int
    count_total: int


class AllocatableResource(BaseModel):
    """sections: [kube_allocatable_cpu_resource_v1, kube_allocatable_memory_resource_v1]"""

    context: Literal["cluster", "node"]
    value: float


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
        raise ValueError(f"Unknown controller type {label} specified")


class Controller(BaseModel):
    type_: ControllerType
    name: str


# A sequence of controllers, e.g. deployment -> replica set. For two adjacent elements, the first
# one controls the second one. The final element controls the pod (but this is not implemented yet).
# Control chains may be incomplete.
ControlChain = Sequence[Controller]


class PodInfo(BaseModel):
    """section: kube_pod_info_v1"""

    namespace: Optional[api.Namespace]
    name: str
    creation_timestamp: Optional[api.CreationTimestamp]
    labels: api.Labels  # used for host labels
    node: Optional[api.NodeName]  # this is optional, because there may be pods, which are not
    # scheduled on any node (e.g., no node with enough capacity is available).
    host_network: Optional[str]
    dns_policy: Optional[str]
    host_ip: Optional[api.IpAddress]
    pod_ip: Optional[api.IpAddress]
    qos_class: api.QosClass
    restart_policy: api.RestartPolicy
    uid: api.PodUID
    # TODO: see CMK-9901
    controllers: ControlChain = []
    cluster: str


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


class PodLifeCycle(BaseModel):
    """section: kube_pod_lifecycle_v1"""

    phase: api.Phase


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


class PodContainers(BaseModel):
    """section: kube_pod_containers_v1"""

    containers: Mapping[str, api.ContainerStatus]


class ContainerSpec(BaseModel):
    image_pull_policy: api.ImagePullPolicy


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


class ReadyCount(BaseModel):
    ready: int = 0
    not_ready: int = 0

    @property
    def total(self) -> int:
        return self.ready + self.not_ready


class NodeCount(BaseModel):
    """section: kube_node_count_v1"""

    worker: ReadyCount = ReadyCount()
    control_plane: ReadyCount = ReadyCount()


class NodeInfo(api.NodeInfo):
    """section: kube_node_info_v1"""

    name: api.NodeName
    creation_timestamp: api.CreationTimestamp
    labels: api.Labels
    addresses: api.NodeAddresses
    cluster: str


class NodeCondition(BaseModel):
    status: api.NodeConditionStatus
    reason: Optional[str]
    detail: Optional[str]
    last_transition_time: Optional[int]


class TruthyNodeCondition(NodeCondition):
    """TruthyNodeCondition has an "OK" state when its status is True"""

    def is_ok(self) -> bool:
        return self.status == api.NodeConditionStatus.TRUE


class FalsyNodeCondition(NodeCondition):
    """FalsyNodeCondition has an "OK" state when its status is False"""

    def is_ok(self) -> bool:
        return self.status == api.NodeConditionStatus.FALSE


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


class DeploymentInfo(BaseModel):
    """section: kube_deployment_info_v1"""

    name: str
    namespace: api.Namespace
    labels: api.Labels
    selector: api.Selector
    creation_timestamp: api.CreationTimestamp
    containers: ThinContainers
    cluster: str


class DaemonSetInfo(BaseModel):
    """section: kube_daemonset_info_v1"""

    name: str
    namespace: api.Namespace
    labels: api.Labels
    selector: api.Selector
    creation_timestamp: api.CreationTimestamp
    cluster: str


class StatefulSetInfo(BaseModel):
    """section: kube_statefulset_info_v1"""

    name: str
    namespace: api.Namespace
    labels: api.Labels
    selector: api.Selector
    creation_timestamp: api.CreationTimestamp
    cluster: str


class DeploymentConditions(BaseModel):
    """section: kube_deployment_conditions_v1"""

    available: Optional[api.DeploymentCondition]
    progressing: Optional[api.DeploymentCondition]
    replicafailure: Optional[api.DeploymentCondition]


class ContainerCount(BaseModel):
    """section: kube_node_container_count_v1"""

    running: int = 0
    waiting: int = 0
    terminated: int = 0


class DeploymentStrategy(BaseModel):
    """section: kube_deployment_strategy_v1"""

    strategy: Union[api.Recreate, api.RollingUpdate] = Field(discriminator="type_")


class DaemonSetStrategy(BaseModel):
    """section: kube_daemonset_strategy_v1"""

    strategy: Union[api.OnDelete, api.RollingUpdate] = Field(discriminator="type_")


class StatefulSetStrategy(BaseModel):
    """section: kube_statefulset_strategy_v1"""

    strategy: Union[api.OnDelete, api.StatefulSetRollingUpdate] = Field(discriminator="type_")


class Memory(BaseModel):
    type_: Literal["memory"] = Field("memory", const=True)
    usage: float


class Cpu(BaseModel):
    type_: Literal["cpu"] = Field("cpu", const=True)
    usage: float


class PerformanceUsage(BaseModel):
    """section: [kube_performance_cpu_v1, kube_performance_memory_v1]"""

    resource: Union[Cpu, Memory] = Field(discriminator="type_")


class ClusterInfo(BaseModel):
    """section: kube_cluster_info_v1"""

    name: str
