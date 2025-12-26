#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
The schemas contained in this file define the stable API between kubernetes and
the special agent.
The schemas should not be affected by different kubernetes server or client versions.

This file should not contain any code and should not import from anywhere
except the python standard library or pydantic.

Guideline when defining new models:
* default values should be written out

class Wrong(BaseModel):
    a: int | None # pydantic implicit None default

class Correct(BaseModel):
    a: int | None = None

"""

# mypy: disable-error-code="mutable-override"
# mypy: disable-error-code="type-arg"

import datetime
import enum
import math
from collections.abc import Mapping, Sequence
from typing import Literal, NewType

from pydantic import BaseModel, ConfigDict, field_validator, model_validator, RootModel
from pydantic.fields import Field

CronJobUID = NewType("CronJobUID", str)
JobUID = NewType("JobUID", str)
PodUID = NewType("PodUID", str)
GitVersion = NewType("GitVersion", str)
ContainerName = NewType("ContainerName", str)
VolumeName = NewType("VolumeName", str)

AnnotationValue = NewType("AnnotationValue", str)
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
        >>> is_prefix_part('a.a')  # Two DNS labels separated by a dot
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


# TODO: introduce NamespacedName as its own type
def namespaced_name(namespace: str, name: str) -> str:
    return f"{namespace}_{name}"


class ClientModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class Label(BaseModel):
    name: LabelName
    value: LabelValue


Labels = Mapping[LabelName, Label]
Annotations = Mapping[LabelName, AnnotationValue]
Timestamp = NewType("Timestamp", float)

# This information is from the one-page API overview v1.22
# Restart policy for all containers within the pod. Default to Always. More info:
RestartPolicy = Literal["Always", "OnFailure", "Never"]

# This information is from the one-page API overview v1.22
# The Quality of Service (QOS) classification assigned to the pod based on resource requirements.
QosClass = Literal["burstable", "besteffort", "guaranteed"]

NamespaceName = NewType("NamespaceName", str)
NodeName = NewType("NodeName", str)
IpAddress = NewType("IpAddress", str)


def parse_cpu_cores(value: str) -> float:
    """Parses and then rounds up to nearest millicore.

    This is how it is done internally by the Kubernetes API server.

    Examples:
       >>> parse_cpu_cores("359m")
       0.359
       >>> parse_cpu_cores("4k")
       4000.0
       >>> parse_cpu_cores("200Mi")
       209715200.0
       >>> parse_cpu_cores("1M")
       1000000.0
    """
    return math.ceil(1000 * _parse_quantity(value)) / 1000


def parse_resource_value(value: str) -> int:
    """Function which converts the reported resource value to its value in the appropriate
    base unit

    millibytes are useless, but valid. This is because Kubernetes uses Quantity everywhere
    https://github.com/kubernetes/kubernetes/issues/28741
    Internally, Kubernetes rounds millibytes up to the nearest byte.

    Targeted resources:
        * memory
        * storage
    """
    return math.ceil(_parse_quantity(value))


def parse_pod_number(value: str) -> int:
    """Yes, pod numbers are described with quantities...

    Examples:
       >>> parse_pod_number("1k")
       1000
    """
    return math.ceil(_parse_quantity(value))


def _parse_quantity(value: str) -> float:
    # Kubernetes uses a common field for any entry in resources, which it refers to as Quantity.
    # See staging/src/k8s.io/apimachinery/pkg/api/resource/quantity.go
    for unit, factor in [
        ("Ki", 1024**1),
        ("Mi", 1024**2),
        ("Gi", 1024**3),
        ("Ti", 1024**4),
        ("Pi", 1024**5),
        ("Ei", 1024**6),
        ("K", 1e3),
        ("k", 1e3),
        ("M", 1e6),
        ("G", 1e9),
        ("T", 1e12),
        ("P", 1e15),
        ("E", 1e18),
        ("m", 1e-3),
    ]:
        if value.endswith(unit):
            return factor * float(value.removesuffix(unit))
    return float(value)


def convert_to_timestamp(kube_date_time: str | datetime.datetime) -> Timestamp:
    if isinstance(kube_date_time, str):
        date_time = datetime.datetime.strptime(kube_date_time, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=datetime.UTC
        )
    elif isinstance(kube_date_time, datetime.datetime):
        date_time = kube_date_time
        if date_time.tzinfo is None:
            raise ValueError(f"Can not convert to timestamp: '{kube_date_time}' is missing tzinfo")
    else:
        raise TypeError(
            f"Can not convert to timestamp: '{kube_date_time}' of type {type(kube_date_time)}"
        )

    return Timestamp(date_time.timestamp())


def parse_labels(labels: Mapping[str, str] | None) -> Mapping[LabelName, Label]:
    if labels is None:
        return {}
    return {LabelName(k): Label(name=LabelName(k), value=LabelValue(v)) for k, v in labels.items()}


def parse_annotations(annotations: Mapping[str, str] | None) -> Annotations:
    """Select annotations, if they are valid.

    Kubernetes allows the annotations to be arbitrary byte strings with a
    length of at most 256Kb. The python client will try to decode these with
    utf8, but appears to return raw data if an exception occurs. We have not
    tested whether this will happen. The current commit, when this information
    was obtained, was
    https://github.com/kubernetes/kubernetes/commit/a83cc51a19d1b5f2b2d3fb75574b04f587ec0054

    Information about the valid syntax and character set can be found here:
    https://kubernetes.io/docs/concepts/overview/working-with-objects/annotations/#syntax-and-character-set
    (Please note that the linked article does not reveal all the relevant information, and we infer
    some further information from the source code directly such as the maximum value length:
    https://github.com/kubernetes/kubernetes/blob/master/staging/src/k8s.io/apimachinery/pkg/api/validation/objectmeta.go#L36)

    Since not every annotation can be converted to a HostLabel, we decided to
    only use annotations, which are also valid Checkmk Host labels and are not longer than a
    specific length.

    Kubernetes makes sure that the annotation has a valid name, so we only verify, that
    the key is also valid as a label.

    >>> parse_annotations(None)  # no annotation specified for the object
    {}
    >>> parse_annotations({
    ... '1': '',
    ... '2': 'a-.',
    ... '3': 'a:',
    ... '4': 'a' * 257,
    ... '5': 'valid-key',
    ... })
    {'1': '', '2': 'a-.', '5': 'valid-key'}
    """
    if annotations is None:
        return {}

    return {
        LabelName(k): AnnotationValue(v)
        for k, v in annotations.items()
        if ":" not in v and len(v) <= 256
    }


class MetaDataNoNamespace(ClientModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    creation_timestamp: Timestamp = Field(..., alias="creationTimestamp")
    labels: Labels = {}
    annotations: Annotations = {}

    _parse_creation_timestamp = field_validator(
        "creation_timestamp", mode="before", check_fields=False
    )(convert_to_timestamp)
    _parse_labels = field_validator("labels", mode="before", check_fields=False)(parse_labels)
    _parse_annotations = field_validator("annotations", mode="before", check_fields=False)(
        parse_annotations
    )


class MetaData(MetaDataNoNamespace):
    model_config = ConfigDict(from_attributes=True)

    namespace: NamespaceName


class NamespaceMetaData(MetaDataNoNamespace):
    name: NamespaceName


class NodeMetaData(MetaDataNoNamespace):
    name: NodeName


class Namespace(ClientModel):
    model_config = ConfigDict(from_attributes=True)

    metadata: NamespaceMetaData


# TODO: PodCrossNamespaceAffinity is currently not supported
# service is not generated
class QuotaScope(enum.Enum):
    """
    General:
        * QuotaScope comprises multiple pod related concepts (QoS class, priority class,
        terminating spec) and can therefore be considered ResourceQuota specific

    Scopes:
        * BestEffort: pods with BestEffort QoS class
        * NotBestEffort: pods with either Burstable and Guaranteed QoS class
        * Terminating: pods that have the active-DeadlineSeconds set (name itself is misleading)
        * NotTerminating: pods that do not have the active-DeadlineSeconds set
        * PriorityClass: pods with an assigned PriorityClass
    """

    BestEffort = "BestEffort"
    NotBestEffort = "NotBestEffort"
    Terminating = "Terminating"
    NotTerminating = "NotTerminating"
    PriorityClass = "PriorityClass"


class ScopeOperator(enum.Enum):
    In = "In"
    NotIn = "NotIn"
    Exists = "Exists"
    DoesNotExist = "DoesNotExist"


class ScopedResourceMatchExpression(BaseModel):
    """
    Definitions 1. - 3. are taken from
    https://kubernetes.io/docs/concepts/policy/resource-quotas/#quota-scopes

    1.  if scopeName is one of these [Terminating, NotTerminating, BestEffort, NotBestEffort], the
    operator MUST be "Exists" (see also 3.)

    2.  if operator is one of ["In", "NotIn"] , the values field must have AT LEAST ONE value

    3.  if operator is one of ["Exists", "DoesNotExist"] , the values field MUST NOT be specified

    4.  Based on 1. and 3.: operator DoesNotExist can only be used for scopeName = PriorityClass
        with an empty values field -> pod.priority_class_name must be None to be valid
    """

    operator: ScopeOperator
    # TODO: CrossNamespacePodAffinity
    scope_name: QuotaScope
    values: Sequence[str]


class HardResourceRequirement(BaseModel):
    limit: float | None = None
    request: float | None = None


class HardRequirement(BaseModel):
    # the format is different to ResourcesRequirement as resources are not nested within
    # request & limit for RQ
    memory: HardResourceRequirement | None = None
    cpu: HardResourceRequirement | None = None


class ScopeSelector(BaseModel):
    match_expressions: Sequence[ScopedResourceMatchExpression]


class ResourceQuotaSpec(BaseModel):
    """
    General:
        * it is possible to set constraints for almost all Kubernetes object types
        (e.g. deployments) but quota scopes usually pod relevant
        (see https://kubernetes.io/docs/concepts/policy/resource-quotas/#quota-scopes for tracking
        scopes)
        * it is possible to specify both scope_selector and scopes fields at the same time

    scopes:
        * only objects which fulfill the intersection of the specified scopes are considered
        part of the RQ.
        * PriorityClass scope verifies if the object has any PriorityClass associated with it
    """

    hard: HardRequirement | None = None
    scope_selector: ScopeSelector | None = None
    scopes: Sequence[QuotaScope] | None = None


class ResourceQuota(BaseModel):
    """
    A resource quota provides constraints (objects count, workload resources) that limit
    aggregate resource consumption per namespace:
        * it can limit the quantity of objects that can be created
        * total amount of compute resources (memory, cpu)

    ResourceQuota controller behaviour:
        * Kubernetes enforces RQ at pod creation time. This means that pods created prior to the RQ
        definition are unaffected

    General:
        * RQ is enabled by default for many distributions (ResourceQuota must be included in
            --enable-admission-plugins=)
        * convention is to create one RQ for each namespace (but Kubernetes does not reject
        multiple RQs targeting the same namespace)
    """

    metadata: MetaData
    spec: ResourceQuotaSpec


class NodeConditionStatus(str, enum.Enum):
    TRUE = "True"
    FALSE = "False"
    UNKNOWN = "Unknown"


class NodeCondition(ClientModel):
    status: NodeConditionStatus
    type_: str = Field(..., alias="type")
    reason: str | None = None
    message: str | None = None


class NodeResources(BaseModel):
    cpu: float = 0.0
    memory: int = 0
    pods: int = 0

    _parse_cpu = field_validator("cpu", mode="before", check_fields=False)(parse_cpu_cores)
    _parse_memory = field_validator("memory", mode="before", check_fields=False)(
        parse_resource_value
    )
    _parse_pods = field_validator("pods", mode="before", check_fields=False)(parse_pod_number)


class HealthZ(BaseModel):
    status_code: int
    response: str


class NodeConnectionError(BaseModel):
    message: str


class APIHealth(BaseModel):
    ready: HealthZ
    live: HealthZ


class KubeletVolumeMetricName(enum.Enum):
    used = "kubelet_volume_stats_used_bytes"
    capacity = "kubelet_volume_stats_capacity_bytes"
    available = "kubelet_volume_stats_available_bytes"


class KubeletVolumeLabels(BaseModel):
    namespace: str
    persistentvolumeclaim: str


class OpenMetricSample(BaseModel):
    metric_name: KubeletVolumeMetricName
    labels: KubeletVolumeLabels
    value: float


class KubeletVolumeMetricSample(OpenMetricSample):
    metric_name: KubeletVolumeMetricName
    labels: KubeletVolumeLabels


class UnusedKubeletMetricSample(BaseModel):
    pass


_KubeletMetrics = KubeletVolumeMetricSample | UnusedKubeletMetricSample


class KubeletMetricSample(RootModel):
    # https://github.com/pydantic/pydantic/issues/675#issuecomment-513029543
    root: _KubeletMetrics


class NodeInfo(ClientModel):
    model_config = ConfigDict(from_attributes=True)

    architecture: str
    kernel_version: str = Field(..., alias="kernelVersion")
    os_image: str = Field(..., alias="osImage")
    operating_system: str = Field(..., alias="operatingSystem")
    container_runtime_version: str = Field(..., alias="containerRuntimeVersion")
    kubelet_version: str = Field(..., alias="kubeletVersion")
    kube_proxy_version: str = Field(..., alias="kubeProxyVersion")


class NodeAddress(ClientModel):
    address: IpAddress
    # according to the docs type_ is "Hostname", "ExternalIP", "InternalIP", but we also saw
    # "InternalDNS" and "ExternalDNS" on an eks cluster
    type_: str = Field(..., alias="type")


NodeAddresses = Sequence[NodeAddress]


class NodeStatus(ClientModel):
    allocatable: NodeResources = NodeResources()
    capacity: NodeResources = NodeResources()
    conditions: Sequence[NodeCondition] | None = None
    node_info: NodeInfo = Field(..., alias="nodeInfo")
    addresses: NodeAddresses = []


def _give_root_if_prefix_present(label: LabelName, prefix: str) -> str | None:
    """
    >>> _give_root_if_prefix_present("123asd", "123")
    'asd'
    >>> _give_root_if_prefix_present("asd123", "123") is None
    True
    >>> _give_root_if_prefix_present("asd", "123") is None
    True
    """
    if label.startswith(prefix):
        return label[len(prefix) :]
    return None


class Node(BaseModel):
    metadata: NodeMetaData
    status: NodeStatus
    kubelet_health: HealthZ | NodeConnectionError

    def roles(self) -> Sequence[str]:
        return [
            role
            for label in self.metadata.labels
            if (role := _give_root_if_prefix_present(label, "node-role.kubernetes.io/")) is not None
        ]


class ReplicasControllerSpec(BaseModel):
    """
    min_ready_seconds:
        * minimum number of secs for which a newly created pod should be ready before considered
        available
        * defaults to 0
    """

    min_ready_seconds: int


class Replicas(BaseModel):
    replicas: int
    updated: int
    available: int
    ready: int
    unavailable: int


class ConditionStatus(enum.StrEnum):
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

    type_: Literal["RollingUpdate"] = Field("RollingUpdate")
    max_surge: str | int  # This field was introduced in Kubernetes v1.21.
    max_unavailable: str | int


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

    type_: Literal["StatefulSetRollingUpdate"] = Field("StatefulSetRollingUpdate")
    partition: int
    max_unavailable: str | int | None = Field(None)


class Recreate(BaseModel):
    type_: Literal["Recreate"] = Field("Recreate")


class OnDelete(BaseModel):
    type_: Literal["OnDelete"] = Field("OnDelete")


class DeploymentSpec(ReplicasControllerSpec):
    strategy: Recreate | RollingUpdate = Field(discriminator="type_")
    selector: Selector


class Deployment(BaseModel):
    metadata: MetaData
    spec: DeploymentSpec
    status: DeploymentStatus
    pods: Sequence[PodUID]


class DaemonSetSpec(ReplicasControllerSpec):
    strategy: OnDelete | RollingUpdate = Field(discriminator="type_")
    selector: Selector


class DaemonSetStatus(BaseModel):
    desired_number_scheduled: int
    updated_number_scheduled: int
    number_misscheduled: int
    number_ready: int
    number_available: int


class DaemonSet(BaseModel):
    metadata: MetaData
    spec: DaemonSetSpec
    status: DaemonSetStatus
    pods: Sequence[PodUID]


class StatefulSetSpec(ReplicasControllerSpec):
    strategy: OnDelete | StatefulSetRollingUpdate = Field(discriminator="type_")
    selector: Selector
    replicas: int


class StatefulSetStatus(BaseModel):
    updated_replicas: int = Field(0, alias="updatedReplicas")
    ready_replicas: int = Field(0, alias="readyReplicas")
    available_replicas: int = Field(0, alias="availableReplicas")


class StatefulSet(BaseModel):
    metadata: MetaData
    spec: StatefulSetSpec
    status: StatefulSetStatus
    pods: Sequence[PodUID]


class Phase(str, enum.Enum):
    RUNNING = "running"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class ResourcesRequirements(BaseModel):
    memory: float | None = None
    cpu: float | None = None


class ContainerResources(BaseModel):
    limits: ResourcesRequirements
    requests: ResourcesRequirements


ImagePullPolicy = Literal["Always", "Never", "IfNotPresent"]


class ContainerSpec(BaseModel):
    resources: ContainerResources
    name: ContainerName
    image_pull_policy: ImagePullPolicy


class VolumePersistentVolumeClaimSource(ClientModel):
    claim_name: str
    read_only: bool | None = None


class Volume(ClientModel):
    """
    name:
        volume's name; must be a dns_label and unique within the pod
    persistent_volume_claim:
        PersistentVolumeClaimVolumeSource represents a reference to a PVC in the same namespace
    """

    name: VolumeName
    persistent_volume_claim: VolumePersistentVolumeClaimSource | None = None


class PodSpec(BaseModel):
    """
    volumes:
        list of volumes that can be mounted by container belonging to the pod
    """

    node: NodeName | None = None
    host_network: bool | None = None
    dns_policy: str | None = None
    restart_policy: RestartPolicy
    containers: Sequence[ContainerSpec]
    init_containers: Sequence[ContainerSpec]
    priority_class_name: str | None = None
    active_deadline_seconds: int | None = None
    volumes: Sequence[Volume] | None = None


@enum.unique
class ContainerStateType(str, enum.Enum):
    running = "running"
    waiting = "waiting"
    terminated = "terminated"


class ContainerRunningState(BaseModel):
    type: Literal[ContainerStateType.running] = Field(ContainerStateType.running)
    start_time: int


class ContainerWaitingState(BaseModel):
    type: Literal[ContainerStateType.waiting] = Field(ContainerStateType.waiting)
    reason: str | None = None
    detail: str | None = Field(None)


class ContainerTerminatedState(BaseModel):
    type: Literal[ContainerStateType.terminated] = Field(ContainerStateType.terminated)
    exit_code: int
    start_time: int | None = None
    end_time: int | None = None
    reason: str | None = None
    detail: str | None = None


ContainerState = ContainerTerminatedState | ContainerWaitingState | ContainerRunningState


class ContainerStatus(BaseModel):
    container_id: str | None = None  # container_id of non-ready container is None
    image_id: str  # image_id of non-ready container is ""
    name: str
    image: str
    ready: bool
    state: ContainerState
    restart_count: int


class ConditionType(str, enum.Enum):
    """
    DISRUPTIONTARGET
        * condition is only present if the pod is actually disrupted by one of listed
        events (in most cases not):
        https://kubernetes.io/docs/concepts/workloads/pods/disruptions/#pod-disruption-conditions
        * simply terminating the pod will not produce this condition
    """

    # https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-conditions
    PODHASNETWORK = "hasnetwork"
    PODREADYTOSTARTCONTAINERS = "readytostartcontainers"
    PODSCHEDULED = "scheduled"
    CONTAINERSREADY = "containersready"
    INITIALIZED = "initialized"
    READY = "ready"
    DISRUPTIONTARGET = "disruptiontarget"


class PodCondition(BaseModel):
    """
    status:
        * when True, reason & detail will be normally None
        * for condition DisruptionTarget will include a reason & detail strings also for True
    """

    status: bool
    type: ConditionType | None = None
    custom_type: str | None = None
    reason: str | None = None
    detail: str | None = None
    last_transition_time: int | None = None

    @model_validator(mode="after")
    @staticmethod
    def verify_type(data: "PodCondition") -> "PodCondition":
        if data.type or data.custom_type:
            # Tests indicate implicit or
            if not (data.type is not None or data.custom_type is not None):
                raise ValueError("either type or custom_type is required")
        return data


class PodStatus(BaseModel):
    conditions: list[PodCondition] | None = None
    phase: Phase
    start_time: Timestamp | None = None  # None if pod is faulty
    host_ip: IpAddress | None = None
    pod_ip: IpAddress | None = None
    qos_class: QosClass | None = None


class Controller(BaseModel):
    # Used to represent top level controllers of a pod
    # Derived from the OwnerReference information in the pod
    # But they may not be the top-level controllers of the pod
    # In the event that they are not the top-level controllers, we go through the OwnerReferences of the intermediary controllers until we find the top-level controller
    # Example:
    # pod "test_pod" is owned by a job named "test_job" and the "test_job" in owned by a cronjob named "test_cronjob"
    # the top-level controller of the "test_pod" is the "test_cronjob"
    type_: str  # Relates to the field kind in OwnerReference
    uid: str
    name: str
    namespace: str | None = None


class Pod(BaseModel):
    uid: PodUID
    metadata: MetaData
    status: PodStatus
    spec: PodSpec
    containers: Mapping[str, ContainerStatus]
    init_containers: Mapping[str, ContainerStatus]
    controllers: Sequence[Controller]


class ConcurrencyPolicy(enum.Enum):
    # specifies how to treat concurrent executions of a Job.
    Allow = "Allow"  # allows concurrently running jobs
    Forbid = "Forbid"  # does not allow concurrent runs
    Replace = "Replace"  # replaces the currently running job


class CronJobSpec(BaseModel):
    concurrency_policy: ConcurrencyPolicy
    schedule: str
    failed_jobs_history_limit: int
    successful_jobs_history_limit: int
    suspend: bool


class CronJobStatus(BaseModel):
    """
    active:
        a list of uids of currently running jobs
    last_schedule_time:
        information when was the last time the job was successfully scheduled (!= finished)
    last_successful_time:
        information when was the last time the job successfully completed
    """

    active: Sequence[JobUID] | None = None
    last_schedule_time: Timestamp | None = None
    last_successful_time: Timestamp | None = None


class CronJob(BaseModel):
    uid: CronJobUID
    metadata: MetaData
    spec: CronJobSpec
    status: CronJobStatus
    pod_uids: Sequence[PodUID]
    job_uids: Sequence[JobUID]


class JobConditionType(enum.Enum):
    COMPLETE = "Complete"
    FAILED = "Failed"
    SUSPENDED = "Suspended"
    SUCCESS_CRITERIA_MET = "Successcriteriamet"
    FAILURE_TARGET = "Failuretarget"


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


class JobStatus(BaseModel):
    """
    * Kubernetes Job Controller creates a pod based on the single pod template in the Job spec -> It
    is not possible to have multiple pods in a Job (https://stackoverflow.com/a/63165871)
    -> but Kubernetes is extensible and one can define its own Custom Resource and write a
    controller which supports multiple pod templates (considered out of scope)

    fields:
        active:
            number of pending & running pods
        failed | succeeded | ready:
            number of pods which reached phase Failed | Succeeded | have a ready condition
        completion_time:
            the completion time is only set when the job finishes successfully
        start_time:
            * represents time when job controller started processing a job
            * When job is created in suspended state, then the value is not set until job is resumed
            * the value is reset when the job transitions from suspended to resumed
            (https://kubernetes.io/blog/2021/04/12/introducing-suspended-jobs/)

    """

    active: int | None = None
    start_time: Timestamp | None = None
    completion_time: Timestamp | None = None
    failed: int | None = None  # it appears that None is equivalent to 0 failed
    succeeded: int | None = None
    conditions: Sequence[JobCondition] | None = None


class Job(BaseModel):
    uid: JobUID
    metadata: MetaData
    status: JobStatus
    pod_uids: Sequence[PodUID]


class StorageRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    storage: int

    _parse_storage = field_validator("storage", mode="before", check_fields=False)(
        parse_resource_value
    )


class StorageResourceRequirements(ClientModel):
    limits: StorageRequirement | None = None
    requests: StorageRequirement | None = None


class PersistentVolumeMode(enum.Enum):
    """PersistentVolumeMode describes how a volume is intended to be consumed

    Block:
        means the volume will not be formatted with a filesystem and will remain
        a raw block device.
    Filesystem:
        means the volume will be or is formatted with a filesystem
    """

    BLOCK = "Block"
    FILESYSTEM = "Filesystem"


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


class PersistentVolumeClaimSpec(ClientModel):
    """
    access_modes:
        contains the desired access modes the volume should have

    resources:
        minimum resources the volume should have

    storage_class_name:
        name of the StorageClass required by the claim

    volume_name:
        VolumeName is the binding reference to the PersistentVolume backing this claim
        (pv.metadata.name)

    """

    model_config = ConfigDict(from_attributes=True)

    access_modes: Sequence[AccessMode] | None = None
    resources: StorageResourceRequirements | None = None
    storage_class_name: str | None = None
    volume_mode: PersistentVolumeMode | None = None
    volume_name: VolumeName | None = None


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


# TODO: bring consistency to models CMK-11887
class PersistentVolumeClaimStatus(ClientModel):
    model_config = ConfigDict(from_attributes=True)

    phase: PersistentVolumeClaimPhase | None = None
    access_modes: Sequence[AccessMode] | None = None
    capacity: StorageRequirement | None = None


class PersistentVolumeClaim(BaseModel):
    metadata: MetaData
    spec: PersistentVolumeClaimSpec
    status: PersistentVolumeClaimStatus


class PersistentVolumeSpec(ClientModel):
    access_modes: list[AccessMode]
    storage_class_name: str | None = None
    volume_mode: str


class PersistentVolume(ClientModel):
    metadata: MetaDataNoNamespace
    spec: PersistentVolumeSpec


class ClusterDetails(BaseModel):
    api_health: APIHealth
    version: GitVersion


class UnknownKubernetesVersion(BaseModel):
    git_version: GitVersion


class KubernetesVersion(BaseModel):
    git_version: GitVersion
    major: int
    minor: int


class OwnerReference(BaseModel):
    uid: str
    controller: bool | None = None  # Optional, since some owner references
    # are user-defined and the controller field can be omitted from the yaml.
    # This model is only intended for parsing. The absence of the controller
    # field can be interpreted as controller=False, but this interpretation is
    # done in _match_controllers, where all the interpretation for owner
    # references happens.
    kind: str
    name: str
    namespace: str | None = None


OwnerReferences = Sequence[OwnerReference]
"""

Example 1: A Pod is owned and controlled by a ReplicaSet with uid 123, then we obtain
`[OwnerReference(uid="123", controller=True)]`

Example 2: The Pod is additionaly owned by a ReplicaSet with uid abc, then we obtain
`[OwnerReference(uid="abc", controller=False), OwnerReference(uid="123", controller=True)]` or
`[OwnerReference(uid="abc", controller=None), OwnerReference(uid="123", controller=True)]`

Example 3: A Node is owned by no object, then we obtain
`[]`, but empty fields are omitted and we obtain `None`
"""
