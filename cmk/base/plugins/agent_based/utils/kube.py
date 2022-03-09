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

LabelValue = NewType("LabelValue", str)
"""

A string consisting of alphanumeric characters, '-', '_' or '.', and must
start and end with an alphanumeric character.

    Examples:
        >>> import re
        >>> validation_value = re.compile(r'(([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9])?')
        >>> is_value = lambda x: bool(validation_value.fullmatch(x))
        >>> is_value('MyName')
        True
        >>> is_value('my.name')
        True
        >>> is_value('123-abc')
        True
        >>> is_value('a..a') # repeating '.', '_' or '-' characters in the middle is ok
        True
        >>> is_value('')  # empty values are allowed
        True
        >>> is_value('a-')  # does not end with alphanumeric character
        False
        >>> is_value('a&a')  # & not allowed
        False
"""

LabelName = NewType("LabelName", str)
"""

A string consisting of a name part and an optional prefix part. The validation
for the name part is the same as that of a `LabelValue`. The prefix part is a
lowercase RFC 1123 DNS subdomain, which consists of lowercase alphanumeric
characters, '-', '_' or '.' Note, that these subdomains are more restrictive
than general DNS domains, which are allowed to have empty DNS labels and DNS
labels with other special characters.

    Examples:
        >>> import re
        >>> validation_name_part = re.compile(r'([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9]')
        >>> is_name_part = lambda x: bool(validation_name_part.fullmatch(x))
        >>> validation_prefix_part = re.compile(r'[a-z0-9]([-a-z0-9]*[a-z0-9])?([.][a-z0-9]([-a-z0-9]*[a-z0-9])?)*')
        >>> is_prefix_part = lambda x: bool(validation_prefix_part.fullmatch(x))
        >>> is_prefix_part('a-a')  #  DNS label
        True
        >>> is_prefix_part('a.a')  # Two DNS labels seperated by a dot
        True
        >>> is_prefix_part('A')  # not a DNS label, upper case not allowed
        False
        >>> is_prefix_part('.a')  # not a prefix, each prefix must start and with a non-empty DNS label
        False
        >>> is_prefix_part('a..a')  # Empty DNS label in the middle is not allowed
        False
        >>> def is_name(x: str) -> bool:
        ...     *prefix_part, name_part = x.split('/', maxsplit=1)
        ...     if len(prefix_part) > 0:
        ...         return is_prefix_part(prefix_part[0]) and is_name_part(name_part)
        ...     return is_name_part(name_part)
        >>> is_name('a')  #  A valid name_part without prefix
        True
        >>> is_name('a/A')  #  A valid name part and a valid prefix part
        True
        >>> is_name('/A')  #  Empty prefix is not allowed
        False
        >>> is_name('./a')  # '.' is not a valid prefix part
        False
        >>> is_name('a/a/a')  #  Multiple slashes are not allowed
        False
"""


class Label(BaseModel):
    name: LabelName
    value: LabelValue


ContainerName = NewType("ContainerName", str)
Labels = Mapping[LabelName, Label]
FilteredAnnotations = Mapping[LabelName, LabelValue]
CreationTimestamp = NewType("CreationTimestamp", float)
HostName = NewType("HostName", str)
IpAddress = NewType("IpAddress", str)
NamespaceName = NewType("NamespaceName", str)
NodeName = NewType("NodeName", str)
OsName = NewType("OsName", str)
PodUID = NewType("PodUID", str)
PodSequence = Sequence[str]
PythonCompiler = NewType("PythonCompiler", str)
Timestamp = NewType("Timestamp", float)
Version = NewType("Version", str)
GitVersion = NewType("GitVersion", str)


# This information is from the one-page API overview v1.22
# Restart policy for all containers within the pod. Default to Always. More info:
RestartPolicy = Literal["Always", "OnFailure", "Never"]


# This information is from the one-page API overview v1.22
# The Quality of Service (QOS) classification assigned to the pod based on resource requirements.
QosClass = Literal["burstable", "besteffort", "guaranteed"]


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


# TODO: CMK-10380 (the change will incompatible)
def kube_labels_to_cmk_labels(labels: Labels) -> HostLabelGenerator:
    """Convert Kubernetes Labels to HostLabels.

    Key-value pairs of Kubernetes labels are valid checkmk labels (see
    `LabelName` and `LabelValue`).

    However, directly yielding `HostLabel(label.name, label.value)` is
    problematic. This is because a user can add labels to their Kubernetes
    objects, which overwrite existing Checkmk labels. For instance, the label
    `cmk/os_name=` would overwrite the cmk label `cmk/os_name:linux`. To
    circumvent this problem, we prepend every label key with
    'cmk/kubernetes/label/'.

    >>> list(kube_labels_to_cmk_labels({
    ... 'k8s.io/app': Label(name='k8s.io/app', value='nginx'),
    ... 'infra': Label(name='infra', value='yes'),
    ... }))
    [HostLabel('cmk/kubernetes/label/k8s.io/app', 'nginx'), HostLabel('cmk/kubernetes/label/infra', 'yes')]
    """
    for label in labels.values():
        if (value := label.value) == "":
            value = LabelValue("true")
        yield HostLabel(f"cmk/kubernetes/label/{label.name}", value)


# TODO: CMK-10380 (the change will incompatible)
def kube_annotations_to_cmk_labels(annotations: FilteredAnnotations) -> HostLabelGenerator:
    """Convert Kubernetes Annotations to HostLabels.

    Kubernetes annotations are not valid Checkmk labels, but agent_kube makes
    sure that annotations only arrive here, if we want to yield it as a
    HostLabel, e.g. a restricted set of characters.

    Directly yielding `HostLabel(annotation.name, annotation.value)` is
    problematic. This is because a user can add annotations to their Kubernetes
    objects, which overwrite existing Checkmk labels. For instance, the
    annotation `cmk/os_name=` would overwrite the cmk label
    `cmk/os_name:linux`. To circumvent this problem, we prepend every
    annotation key with 'cmk/kubernetes/annotation/'.

    >>> annotations = {
    ... 'k8s.io/app': 'nginx',
    ... 'infra': 'yes',
    ... 'empty': '',
    ... }
    >>> list(kube_annotations_to_cmk_labels(annotations))
    [HostLabel('cmk/kubernetes/annotation/k8s.io/app', 'nginx'), HostLabel('cmk/kubernetes/annotation/infra', 'yes'), HostLabel('cmk/kubernetes/annotation/empty', 'true')]
    """
    for name, value in annotations.items():
        yield HostLabel(f"cmk/kubernetes/annotation/{name}", value or "true")


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
    """section: kube_node_conditions_v1"""

    ready: TruthyNodeCondition
    memorypressure: FalsyNodeCondition
    diskpressure: FalsyNodeCondition
    pidpressure: FalsyNodeCondition
    networkunavailable: Optional[FalsyNodeCondition]


class NodeCustomConditions(BaseModel):
    """section: kube_node_custom_conditions_v1"""

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
    version: GitVersion


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
    annotations: FilteredAnnotations
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

    namespace: Optional[NamespaceName]
    name: str
    creation_timestamp: Optional[CreationTimestamp]
    labels: Labels  # used for host labels
    annotations: FilteredAnnotations  # used for host labels
    node: Optional[NodeName]  # this is optional, because there may be pods, which are not
    # scheduled on any node (e.g., no node with enough capacity is available).
    host_network: Optional[str]
    dns_policy: Optional[str]
    host_ip: Optional[IpAddress]
    pod_ip: Optional[IpAddress]
    qos_class: Optional[QosClass]  # can be None, if the Pod was evicted.
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


@enum.unique
class ContainerStateType(str, enum.Enum):
    running = "running"
    waiting = "waiting"
    terminated = "terminated"


class ContainerRunningState(BaseModel):
    type: Literal[ContainerStateType.running] = Field(ContainerStateType.running, const=True)
    start_time: int


class ContainerWaitingState(BaseModel):
    type: Literal[ContainerStateType.waiting] = Field(ContainerStateType.waiting, const=True)
    reason: str
    detail: Optional[str]


class ContainerTerminatedState(BaseModel):
    type: Literal[ContainerStateType.terminated] = Field(ContainerStateType.terminated, const=True)
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
    namespace: NamespaceName
    labels: Labels
    annotations: FilteredAnnotations
    selector: Selector
    creation_timestamp: CreationTimestamp
    containers: ThinContainers
    cluster: str


class DaemonSetInfo(BaseModel):
    """section: kube_daemonset_info_v1"""

    name: str
    namespace: NamespaceName
    labels: Labels
    annotations: FilteredAnnotations
    selector: Selector
    creation_timestamp: CreationTimestamp
    containers: ThinContainers
    cluster: str


class StatefulSetInfo(BaseModel):
    """section: kube_statefulset_info_v1"""

    name: str
    namespace: NamespaceName
    labels: Labels
    annotations: FilteredAnnotations
    selector: Selector
    creation_timestamp: CreationTimestamp
    containers: ThinContainers
    cluster: str


class PodContainers(BaseModel):
    """section: kube_pod_containers_v1"""

    containers: Mapping[str, ContainerStatus]


class RollingUpdate(BaseModel):
    """

    This model is used for DaemonSets and Deployments. Although the models are
    identical, the underlying strategies differ for the two. For a Deployment,
    max_unavailable refers to how much the old ReplicaSet can be scaled down.
    Thus, max_unavailable refers to the maximum number of Pods that may be
    unavailable during the update. max_unavailable for a DaemonSet refers to
    the number of Nodes that should be running the daemon Pod (despite what is
    mentioned in the docs). If the number of Nodes with unavailable daemon Pods
    reaches max_unavailable, then Kubernetes will not stop Pods on other Nodes
    in order to update them. The same distinction applies to max_surge.

    The documentation claims, that only one DaemonSet Pod is created, but as of
    v1.21, max_surge allows a second Pod to be scheduled for the duration of
    the update.
    """

    type_: Literal["RollingUpdate"] = Field("RollingUpdate", const=True)
    max_surge: str  # This field was introduced in Kubernetes v1.21.
    max_unavailable: str


class Recreate(BaseModel):
    type_: Literal["Recreate"] = Field("Recreate", const=True)


class OnDelete(BaseModel):
    type_: Literal["OnDelete"] = Field("OnDelete", const=True)


class StatefulSetRollingUpdate(BaseModel):
    type_: Literal["StatefulSetRollingUpdate"] = Field("StatefulSetRollingUpdate", const=True)
    partition: int


DisplayableStrategy = Union[OnDelete, Recreate, RollingUpdate, StatefulSetRollingUpdate]


class UpdateStrategy(BaseModel):
    """section: kube_update_strategy_v1"""

    strategy: DisplayableStrategy = Field(discriminator="type_")


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


class NamespaceInfo(BaseModel):
    """section: kube_namespace_info_v1"""

    name: NamespaceName
    creation_timestamp: Optional[CreationTimestamp]
    labels: Labels
    annotations: FilteredAnnotations
    cluster: str


class IdentificationError(BaseModel):
    """Errors due to incorrect labels set by the user."""

    duplicate_machine_collector: bool
    duplicate_container_collector: bool
    unknown_collector: bool


class NodeCollectorReplica(BaseModel):
    # This model reports api data of a node collector DaemonSet.
    # We identify this DaemonSet via certain labels and provide the counts to the
    # Cluster object via the CollectorDaemons section. The data is also available in
    # a more generic way as part of the Replicas service on a DaemonSet, but we want
    # to show this information on the cluster object.
    available: int
    desired: int


class CollectorDaemons(BaseModel):
    """section: kube_collector_daemons_v1

    Model containing information about the DaemonSets of the node-collectors.
    The section is intended for the cluster host. `None` indicates, that the
    corresponding DaemonSet is not among the API data.
    """

    machine: Optional[NodeCollectorReplica]
    container: Optional[NodeCollectorReplica]
    errors: IdentificationError
