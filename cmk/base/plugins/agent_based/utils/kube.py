#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
import time
from typing import (
    Callable,
    Literal,
    Mapping,
    NewType,
    Optional,
    Sequence,
    Tuple,
    TypedDict,
    TypeVar,
    Union,
)

from pydantic import BaseModel, Field
from typing_extensions import assert_never

from cmk.base.plugins.agent_based.agent_based_api.v1 import HostLabel
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    HostLabelGenerator,
)

COLLECTOR_SERVICE_NAME = "Cluster collector"

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


class ConcurrencyPolicy(enum.Enum):
    # specifies how to treat concurrent executions of a Job.
    Allow = "Allow"  # allows concurrently running jobs
    Forbid = "Forbid"  # does not allow concurrent runs
    Replace = "Replace"  # replaces the currently running job


class Section(BaseModel):
    class Config:
        allow_mutation = False


class Controller(BaseModel):
    type_: str
    name: str


# A sequence of controllers, e.g. deployment -> replica set. For two adjacent elements, the first
# one controls the second one. The final element controls the pod (but this is not implemented yet).
# Control chains may be incomplete.
ControlChain = Sequence[Controller]


def condition_short_description(name: str, status: bool | str) -> str:
    return f"{name.upper()}: {status}"


def condition_detailed_description(
    name: str,
    status: bool | str,
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


class AccessMode(enum.Enum):
    """

    Context:
        providers will have different capabilities and each PV's access modes are set to the
        specific modes supported by the particular volume.
        Each PV gets its own set of access modes describing that specific PV's capabilities

    Modes:
        ReadWriteOnce (RWO):
            * volume can be mounted as read-write by a single node
            * can still allow multiple pods to access the volume when the pods are running on same
            node

        ReadOnlyMany (ROX):
            * volume can be mounted as read-only by many nodes

        ReadWriteMany (RWX):
            * volume can be mounted as read-write by many nodes

        ReadWriteOncePod (RWOP):
            * volume can be mounted as read-write by a single pod
            * use of this mode ensures that only one pod across the whole cluster can read that PVC
            or write to it
            * only supported for CSI volumes and Kubernetes version 1.22+

    """

    READ_WRITE_ONCE = "ReadWriteOnce"
    READ_ONLY_MANY = "ReadOnlyMany"
    READ_WRITE_MANY = "ReadWriteMany"
    READ_WRITE_ONCE_POD = "ReadWriteOncePod"


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


class CollectorComponentsMetadata(Section):
    """section: kube_collector_metadata_v1"""

    processing_log: CollectorHandlerLog
    cluster_collector: Optional[ClusterCollectorMetadata]
    nodes: Optional[Sequence[NodeMetadata]]


class CollectorProcessingLogs(Section):
    """section: kube_collector_processing_logs_v1"""

    container: CollectorHandlerLog
    machine: CollectorHandlerLog


class Phase(str, enum.Enum):
    RUNNING = "running"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class BasePodLifeCycle(BaseModel):
    phase: Phase


class PodLifeCycle(Section, BasePodLifeCycle):
    """section: kube_pod_lifecycle_v1"""


class NodeConditionStatus(str, enum.Enum):
    TRUE = "True"
    FALSE = "False"
    UNKNOWN = "Unknown"


class CountableNode(BaseModel):
    ready: bool
    roles: Sequence[str]


class NodeCount(Section):
    """section: kube_node_count_v1"""

    nodes: Sequence[CountableNode]


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


class NodeConditions(Section):
    """section: kube_node_conditions_v1"""

    ready: TruthyNodeCondition
    memorypressure: FalsyNodeCondition
    diskpressure: FalsyNodeCondition
    pidpressure: FalsyNodeCondition
    networkunavailable: Optional[FalsyNodeCondition]


class NodeCustomConditions(Section):
    """section: kube_node_custom_conditions_v1"""

    custom_conditions: Sequence[FalsyNodeCustomCondition]


class ConditionStatus(enum.StrEnum):
    TRUE = "True"
    FALSE = "False"
    UNKNOWN = "Unknown"


class DeploymentCondition(BaseModel):
    status: ConditionStatus
    last_transition_time: float
    reason: str
    message: str


class DeploymentConditions(Section):
    """section: kube_deployment_conditions_v1"""

    available: Optional[DeploymentCondition]
    progressing: Optional[DeploymentCondition]
    replicafailure: Optional[DeploymentCondition]


class ClusterInfo(Section):
    """section: kube_cluster_info_v1"""

    name: str
    version: GitVersion


VSResultAge = Union[Tuple[Literal["levels"], Tuple[int, int]], Literal["no_levels"]]


def get_age_levels_for(params: Mapping[str, VSResultAge], key: str) -> Optional[Tuple[int, int]]:
    """Get the levels for the given key from the params

    Examples:
        >>> params = dict(
        ...     initialized="no_levels",
        ...     scheduled=("levels", (89, 179)),
        ...     containersready="no_levels",
        ...     ready=("levels", (359, 719)),
        ... )
        >>> get_age_levels_for(params, "initialized")
        >>> get_age_levels_for(params, "scheduled")
        (89, 179)
        >>> get_age_levels_for(params, "containersready")
        >>> get_age_levels_for(params, "ready")
        (359, 719)
        >>> get_age_levels_for({}, "ready")
    """
    levels = params.get(key, "no_levels")
    if levels == "no_levels":
        return None
    return levels[1]


class NodeAddress(BaseModel):
    address: IpAddress
    # according to the docs type_ is "Hostname", "ExternalIP", "InternalIP", but we also saw
    # "InternalDNS" and "ExternalDNS" on an eks cluster
    type_: str = Field(..., alias="type")

    class Config:
        allow_population_by_field_name = True


NodeAddresses = Sequence[NodeAddress]


class NodeInfo(Section):
    """section: kube_node_info_v1"""

    architecture: str
    kernel_version: str
    os_image: str
    operating_system: str
    container_runtime_version: str
    name: NodeName
    creation_timestamp: Timestamp
    labels: Labels
    annotations: FilteredAnnotations
    addresses: NodeAddresses
    cluster: str
    kubernetes_cluster_hostname: str


class HealthZ(BaseModel):
    status_code: int
    response: str
    # only set if status_code != 200
    verbose_response: Optional[str]


class KubeletInfo(Section):
    """section: kube_node_kubelet_v1"""

    version: str
    proxy_version: str
    health: HealthZ


class APIHealth(BaseModel):
    ready: HealthZ
    live: HealthZ


class PodInfo(Section):
    """section: kube_pod_info_v1"""

    namespace: Optional[NamespaceName]
    name: str
    creation_timestamp: Optional[Timestamp]
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
    kubernetes_cluster_hostname: str


class ClusterDetails(Section):
    """section: kube_cluster_details_v1"""

    api_health: APIHealth


class PodResources(Section):
    """section: kube_pod_resources_v1"""

    running: PodSequence = []
    pending: PodSequence = []
    succeeded: PodSequence = []
    failed: PodSequence = []
    unknown: PodSequence = []


class AllocatablePods(Section):
    """section: kube_allocatable_pods_v1"""

    capacity: int
    allocatable: int


class ContainerCount(Section):
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


class PerformanceUsage(Section):
    """section: [kube_performance_cpu_v1, kube_performance_memory_v1]"""

    resource: Union[Cpu, Memory] = Field(discriminator="type_")


class StartTime(Section):
    """section: kube_start_time_v1"""

    start_time: Timestamp


class PodCondition(BaseModel):
    status: bool
    reason: Optional[str]
    detail: Optional[str]
    last_transition_time: Optional[int]


class PodConditions(Section):
    """section: kube_pod_conditions_v1"""

    initialized: Optional[PodCondition]
    hasnetwork: PodCondition | None = None
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
    start_time: Optional[int]
    end_time: Optional[int]
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


class ContainerSpecs(Section):
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


class DeploymentInfo(Section):
    """section: kube_deployment_info_v1"""

    name: str
    namespace: NamespaceName
    labels: Labels
    annotations: FilteredAnnotations
    selector: Selector
    creation_timestamp: Timestamp
    containers: ThinContainers
    cluster: str
    kubernetes_cluster_hostname: str


class DaemonSetInfo(Section):
    """section: kube_daemonset_info_v1"""

    name: str
    namespace: NamespaceName
    labels: Labels
    annotations: FilteredAnnotations
    selector: Selector
    creation_timestamp: Timestamp
    containers: ThinContainers
    cluster: str
    kubernetes_cluster_hostname: str


class StatefulSetInfo(Section):
    """section: kube_statefulset_info_v1"""

    name: str
    namespace: NamespaceName
    labels: Labels
    annotations: FilteredAnnotations
    selector: Selector
    creation_timestamp: Timestamp
    containers: ThinContainers
    cluster: str
    kubernetes_cluster_hostname: str


class PodContainers(Section):
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
    """
    max_unavailable:
        * only available since 1.24
        * requirement: the field is only honored by servers that enable the
        MaxUnavailableStatefulSet gate-feature (https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/)
        * maximum number of pods that can be unavailable during the update
        * value can be an absolute number or a percentage of desired pods (10%); absolute number is
        calculate from percentage by rounding up
        * defaults to 1 (which is the same behaviour as pre 1.24)
        * field applies to all pods in the range 0 to (replicas - 1); any unavailable pod in the
        range 0 to (replicas -1) will be counted towards maxunavailable

    """

    type_: Literal["StatefulSetRollingUpdate"] = Field("StatefulSetRollingUpdate", const=True)
    partition: int
    max_unavailable: str | None


DisplayableStrategy = OnDelete | Recreate | RollingUpdate | StatefulSetRollingUpdate


class UpdateStrategy(Section):
    """section: kube_update_strategy_v1"""

    strategy: DisplayableStrategy = Field(discriminator="type_")


class ControllerSpec(Section):
    """section: kube_controller_spec_v1"""

    min_ready_seconds: int


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

    available: int
    desired: int
    ready: int
    updated: int


class DaemonSetReplicas(Section, CommonReplicas):
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


class StatefulSetReplicas(Section, CommonReplicas):
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


class DeploymentReplicas(Section, CommonReplicas):
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


class NamespaceInfo(Section):
    """section: kube_namespace_info_v1"""

    name: NamespaceName
    creation_timestamp: Optional[Timestamp]
    labels: Labels
    annotations: FilteredAnnotations
    cluster: str
    kubernetes_cluster_hostname: str


class CronJobInfo(Section):
    """section: kube_cron_job_info_v1"""

    name: str
    namespace: NamespaceName
    creation_timestamp: Optional[Timestamp]
    labels: Labels
    annotations: FilteredAnnotations
    schedule: str
    concurrency_policy: ConcurrencyPolicy
    failed_jobs_history_limit: int
    successful_jobs_history_limit: int
    suspend: bool
    cluster: str
    kubernetes_cluster_hostname: str


class JobConditionType(enum.Enum):
    COMPLETE = "Complete"
    FAILED = "Failed"
    SUSPENDED = "Suspended"


class JobCondition(BaseModel):
    """
    Remember: on job status level, conditions is a list of conditions
    Scenarios:
        * Job fails: type="Failed" & status is true
        * Job suspended: type="Suspended" & status is true
        * Job resumes: one of the status will become false
        * Job completed: type="Complete" status true
    """

    type_: JobConditionType
    status: ConditionStatus


class JobPod(BaseModel):
    init_containers: Mapping[str, ContainerStatus]
    containers: Mapping[str, ContainerStatus]
    lifecycle: BasePodLifeCycle


class JobStatus(BaseModel):
    conditions: Sequence[JobCondition]
    start_time: Timestamp | None
    completion_time: Timestamp | None


class CronJobStatus(Section):
    """section: kube_cron_job_status_v1"""

    active_jobs_count: int | None
    last_duration: float | None
    last_successful_time: Timestamp | None
    last_schedule_time: Timestamp | None


class CronJobLatestJob(Section):
    """section: kube_cron_job_latest_job_v1"""

    status: JobStatus
    pods: Sequence[JobPod]


class PersistentVolumeClaimPhase(enum.Enum):
    """
    pending:
        PVCs that are not yet bound
    bound:
        PVCs that are bound
    lost:
        PVCs that lost their underlying PV. The claim was bound to a PV which no longer exists,
        and all data on it is lost
    """

    CLAIM_PENDING = "Pending"
    CLAIM_BOUND = "Bound"
    CLAIM_LOST = "Lost"


class StorageRequirement(BaseModel):
    storage: float


class PersistentVolumeClaimStatus(BaseModel):
    phase: PersistentVolumeClaimPhase | None
    capacity: StorageRequirement | None


class PersistentVolumeClaimMetaData(BaseModel):
    name: str
    namespace: NamespaceName


class PersistentVolumeClaim(BaseModel):
    metadata: PersistentVolumeClaimMetaData
    status: PersistentVolumeClaimStatus
    volume_name: str | None = None


class PersistentVolumeClaims(Section):
    """section: kube_pvc_v1"""

    claims: Mapping[str, PersistentVolumeClaim]


class PersistentVolumeSpec(BaseModel):
    access_modes: list[AccessMode]
    storage_class_name: str | None = None
    volume_mode: str


class PersistentVolume(BaseModel):
    name: str
    spec: PersistentVolumeSpec


class AttachedPersistentVolumes(Section):
    """section: kube_pvc_pvs_v1"""

    volumes: Mapping[str, PersistentVolume]


class AttachedVolume(BaseModel):
    """The PV from a kubelet metrics representation"""

    capacity: float
    free: float
    persistent_volume_claim: str
    namespace: str


class PersistentVolumeClaimAttachedVolumes(Section):
    """section: kube_pvc_volumes_v1"""

    volumes: Mapping[str, AttachedVolume]


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


class CollectorDaemons(Section):
    """section: kube_collector_daemons_v1

    Model containing information about the DaemonSets of the node-collectors.
    The section is intended for the cluster host. `None` indicates, that the
    corresponding DaemonSet is not among the API data.
    """

    machine: Optional[NodeCollectorReplica]
    container: Optional[NodeCollectorReplica]
    errors: IdentificationError


T = TypeVar("T", bound=Section)


def check_with_time(
    check_function: Callable[[float, T], CheckResult]
) -> Callable[[T], CheckResult]:
    def check_function_with_time(section: T) -> CheckResult:
        yield from check_function(time.time(), section)

    return check_function_with_time


def pod_status_message(
    pod_containers: Sequence[ContainerStatus],
    pod_init_containers: Sequence[ContainerStatus],
    section_kube_pod_lifecycle: PodLifeCycle | BasePodLifeCycle,
) -> str:
    if init_container_message := _pod_container_message(pod_init_containers):
        return f"Init:{init_container_message}"
    if container_message := _pod_container_message(pod_containers):
        return container_message
    return section_kube_pod_lifecycle.phase.title()


def _pod_container_message(pod_containers: Sequence[ContainerStatus]) -> Optional[str]:
    containers = erroneous_or_incomplete_containers(pod_containers)
    for container in containers:
        if (
            isinstance(container.state, ContainerWaitingState)
            and container.state.reason != "ContainerCreating"
        ):
            return container.state.reason
    for container in containers:
        if (
            isinstance(container.state, ContainerTerminatedState)
            and container.state.reason is not None
        ):
            return container.state.reason
    return None


def erroneous_or_incomplete_containers(
    containers: Sequence[ContainerStatus],
) -> Sequence[ContainerStatus]:
    return [
        container
        for container in containers
        if not isinstance(container.state, ContainerRunningState)
        and not (
            isinstance(container.state, ContainerTerminatedState) and container.state.exit_code == 0
        )
    ]


class ResultType(enum.Enum):
    request_exception = "request_exception"
    json_decode_error = "json_decode_error"
    validation_error = "validation_error"
    response_error = "response_error"
    response_invalid_data = "reponse_invalid_data"
    response_empty_result = "reponse_empty_result"
    success = "success"


class PrometheusResult(BaseModel):
    """Serialize exceptions."""

    query_: str
    type_: ResultType
    details: str | None

    def summary(self) -> str:
        match self.type_:
            case ResultType.request_exception:
                return f"Request Exception: {self.details}"
            case ResultType.json_decode_error:
                return "Invalid response: did not receive JSON"
            case ResultType.validation_error:
                return "Invalid response: did not match Prometheus HTTP API"
            case ResultType.response_error:
                return f"Prometheus error: {self.details}"
            case ResultType.response_empty_result:
                return "Querying endpoint succeeded, but no samples received"
            case ResultType.response_invalid_data:
                return (
                    "Incompatible data received: data did not match format expected from OpenShift"
                )
            case ResultType.success:
                return "Successfully queried usage data from Prometheus"
        assert_never(self.type_)


class OpenShiftEndpoint(Section):
    """section: prometheus_debug_v1"""

    url: str
    results: Sequence[PrometheusResult]
