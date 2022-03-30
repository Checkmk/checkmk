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


class NamespaceInfo(BaseModel):
    """section: kube_namespace_info_v1"""

    name: api.NamespaceName
    creation_timestamp: Optional[api.CreationTimestamp]
    labels: api.Labels
    cluster: str


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
    daemonset = "daemonset"
    statefulset = "statefulset"

    @staticmethod
    def from_str(label):
        if label == "deployment":
            return ControllerType.deployment
        if label == "daemonset":
            return ControllerType.daemonset
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

    namespace: Optional[api.NamespaceName]
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
    namespace: api.NamespaceName
    labels: api.Labels
    selector: api.Selector
    creation_timestamp: api.CreationTimestamp
    containers: ThinContainers
    cluster: str


class DaemonSetInfo(BaseModel):
    """section: kube_daemonset_info_v1"""

    name: str
    namespace: api.NamespaceName
    labels: api.Labels
    selector: api.Selector
    creation_timestamp: api.CreationTimestamp
    containers: ThinContainers
    cluster: str


class StatefulSetInfo(BaseModel):
    """section: kube_statefulset_info_v1"""

    name: str
    namespace: api.NamespaceName
    labels: api.Labels
    selector: api.Selector
    creation_timestamp: api.CreationTimestamp
    containers: ThinContainers
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


DisplayableStrategy = Union[
    api.OnDelete, api.Recreate, api.RollingUpdate, api.StatefulSetRollingUpdate
]


class UpdateStrategy(BaseModel):
    """section: kube_update_strategy_v1"""

    strategy: DisplayableStrategy = Field(discriminator="type_")


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
    version: api.GitVersion


class ClusterDetails(BaseModel):
    """section: kube_cluster_details_v1"""

    api_health: api.APIHealth


class CommonReplicas(BaseModel):
    """Model shared among controllers.

    Note: All controllers are relatively similiar in how they claim a Pod. A Pod will be claimed
    if the following criterions match:
    * the Selector matches
    * the Pods controller field is empty or equal to that of the claiming Controller
    * the Pod is not Succeeded or Failed
    * neither the Pod nor the Controller have been deleted (DeletionTimestamp is null)
    Note, that this list is somewhat heuristic and reality is a bit more complicated. For instance,
    a Pod can sometimes still be claimed, if the DaemonSet has been deleted.
    """

    desired: int
    ready: int
    updated: int


class DaemonSetReplicas(CommonReplicas):
    """section: kube_daemonset_replicas_v1

    Model for a given DaemonSet supplied to the kube_replicas check.

    The key distinction to Deployments and StatefulSets is the fact, that this section counts Nodes
    rather than Pods. On each Node only the oldest Pod is considered, that has been claimed by the
    DaemonSet.
    """

    # desired (status.desiredNumberScheduled): the number of Nodes, which match the NodeAffinity
    # specified by the DaemonSet.
    # ready (status.numberReady): the number of Nodes, where the oldest claimed Pod is ready.
    # updated (status.updatedNumberScheduled): the number of Nodes, where the oldest claimed Pod is
    # updated. A Pod is updated, if the hash of the Pod template matches the template of the
    # DaemonSet.
    # misscheduled (status.numberMisscheduled): the number of Nodes, on which there is a Pod claimed
    # by the DaemonSet (not necessarily running or ready), but which is not supposed to run a
    # daemon Pod (since the NodeSelector or NodeAffinity term does not match the Node). In
    # particular, there is no overlap between Nodes counted by desired and Nodes counted by
    # misscheduled.
    misscheduled: int


class StatefulSetReplicas(CommonReplicas):
    """section: kube_statefulset_replicas_v1

    Model for a given StatefulSet supplied to the kube_replicas check.

    The key distinction to DaemonSets and Deployments is the concept of ordinals. Ordinals give Pods
    a unique identity, which is persistent across being rescheduled on a different Node. The ordinal
    affects the order of creation and updates (see below).
    """

    # desired (spec.replicas): the number of Pods, which should be claimed, available and up-to-date
    # ready (status.readyReplicas): the number of claimed Pods, which are ready. StatefulSets can
    # achieve readiness in different fashions depending on the value of spec.podManagementPolicy.
    # By default, a new Pod is only created after all the Pods with lower ordinals (the ordinal is
    # appended to the name of the Pod) are available. As of Kubernetes v1.7 Pods can be configured
    # to be created in parallel.
    # updated (status.updatedReplicas): the number of claimed Pods, which match updateRevision of
    # the StatefulSet. The StatefulSet only allows updating in order of the ordinals. Unlike the Pod
    # creation, this behaviour can't be configured as of v1.23.


class DeploymentReplicas(CommonReplicas):
    """section: kube_deployment_replicas_v1

    Model for a given Deployment supplied to the kube_replicas check.

    The key distinction to DaemonSets and StatefulSets is that Deployments manage their Pods via
    ReplicaSets. A Deployment controls either one or two ReplicaSets. The second ReplicaSet is
    created whenever a Deployment needs to update its Pods. The quantities in status of Deployment
    are often sums over the status of the two ReplicaSets.

    Example: The number of unavailableReplicas may be twice the number of desired replicas, because
    it corresponds to the number of Pods not available for both ReplicaSets. Whereas for other
    controllers unavailableReplicas (StatefulSet) or numberUnavailable (DaemonSet) is equal to
    desired - availableReplicas or desired - numberAvailable.
    """

    # desired (spec.replicas): the number of Pods, which should be claimed, available and
    # up-to-date.
    # ready (status.readyReplicas): the number of claimed Pods, which are ready. This is calculated
    # across both ReplicaSets (if present).
    # updated (status.updatedReplicas): the number of claimed Pods, belonging the ReplicaSet with
    # the up-to-date Pod template.
