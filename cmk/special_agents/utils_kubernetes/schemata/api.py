#!/usr/bin/env python3
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
from typing import (
    Dict,
    Generic,
    List,
    Literal,
    Mapping,
    NewType,
    Optional,
    Sequence,
    TypeVar,
    Union,
)

from pydantic import BaseModel
from pydantic.class_validators import validator
from pydantic.fields import Field
from pydantic.generics import GenericModel

CronJobUID = NewType("CronJobUID", str)
JobUID = NewType("JobUID", str)
PodUID = NewType("PodUID", str)
GitVersion = NewType("GitVersion", str)
ContainerName = NewType("ContainerName", str)

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


Labels = Mapping[LabelName, Label]
Annotations = Mapping[LabelName, LabelValue]
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

ObjectName = TypeVar("ObjectName", bound=str)


class MetaDataNoNamespace(GenericModel, Generic[ObjectName]):
    name: ObjectName
    creation_timestamp: Timestamp
    labels: Labels
    annotations: Annotations


class MetaData(MetaDataNoNamespace[ObjectName], Generic[ObjectName]):
    namespace: NamespaceName


class Namespace(BaseModel):
    metadata: MetaDataNoNamespace[NamespaceName]


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
    limit: Optional[float] = None
    request: Optional[float] = None


class HardRequirement(BaseModel):
    # the format is different to ResourcesRequirement as resources are not nested within
    # request & limit for RQ
    memory: Optional[HardResourceRequirement] = None
    cpu: Optional[HardResourceRequirement] = None


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

    hard: Optional[HardRequirement]
    scope_selector: Optional[ScopeSelector]
    scopes: Optional[Sequence[QuotaScope]]


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

    metadata: MetaData[str]
    spec: ResourceQuotaSpec


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
    cpu: float = 0.0
    memory: float = 0.0
    pods: int = 0


class HealthZ(BaseModel):
    status_code: int
    response: str
    # only set if status_code != 200
    verbose_response: Optional[str]


class APIHealth(BaseModel):
    ready: HealthZ
    live: HealthZ


class KubeletInfo(BaseModel):
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
    metadata: MetaDataNoNamespace[NodeName]
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


class StatefulSetRollingUpdate(BaseModel):
    type_: Literal["StatefulSetRollingUpdate"] = Field("StatefulSetRollingUpdate", const=True)
    partition: int


class Recreate(BaseModel):
    type_: Literal["Recreate"] = Field("Recreate", const=True)


class OnDelete(BaseModel):
    type_: Literal["OnDelete"] = Field("OnDelete", const=True)


class DeploymentSpec(BaseModel):
    strategy: Union[Recreate, RollingUpdate] = Field(discriminator="type_")
    selector: Selector


class Deployment(BaseModel):
    metadata: MetaData[str]
    spec: DeploymentSpec
    status: DeploymentStatus
    pods: Sequence[PodUID]


class DaemonSetSpec(BaseModel):
    strategy: Union[OnDelete, RollingUpdate] = Field(discriminator="type_")
    selector: Selector


class DaemonSetStatus(BaseModel):
    desired_number_scheduled: int
    updated_number_scheduled: int
    number_misscheduled: int
    number_ready: int
    number_available: int


class DaemonSet(BaseModel):
    metadata: MetaData[str]
    spec: DaemonSetSpec
    status: DaemonSetStatus
    pods: Sequence[PodUID]


class StatefulSetSpec(BaseModel):
    strategy: Union[OnDelete, StatefulSetRollingUpdate] = Field(discriminator="type_")
    selector: Selector
    replicas: int


class StatefulSetStatus(BaseModel):
    updated_replicas: int
    ready_replicas: int


class StatefulSet(BaseModel):
    metadata: MetaData[str]
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
    memory: Optional[float] = None
    cpu: Optional[float] = None


class ContainerResources(BaseModel):
    limits: ResourcesRequirements
    requests: ResourcesRequirements


ImagePullPolicy = Literal["Always", "Never", "IfNotPresent"]


class ContainerSpec(BaseModel):
    resources: ContainerResources
    name: ContainerName
    image_pull_policy: ImagePullPolicy


class PodSpec(BaseModel):
    node: Optional[NodeName] = None
    host_network: Optional[str] = None
    dns_policy: Optional[str] = None
    restart_policy: RestartPolicy
    containers: Sequence[ContainerSpec]
    init_containers: Sequence[ContainerSpec]
    priority_class_name: Optional[str] = None
    active_deadline_seconds: Optional[int] = None


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


ContainerState = Union[ContainerTerminatedState, ContainerWaitingState, ContainerRunningState]


class ContainerStatus(BaseModel):
    container_id: Optional[str]  # container_id of non-ready container is None
    image_id: str  # image_id of non-ready container is ""
    name: str
    image: str
    ready: bool
    state: ContainerState
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
    last_transition_time: Optional[int]

    @validator("custom_type")
    @classmethod
    def verify_type(cls, v, values):
        if "type" not in values and not v:
            raise ValueError("either type or custom_type is required")
        return v


class PodStatus(BaseModel):
    conditions: Optional[List[PodCondition]]
    phase: Phase
    start_time: Optional[Timestamp]  # None if pod is faulty
    host_ip: Optional[IpAddress] = None
    pod_ip: Optional[IpAddress] = None
    qos_class: Optional[QosClass]


class ControllerType(enum.Enum):
    deployment = "deployment"
    daemonset = "daemonset"
    statefulset = "statefulset"
    cronjob = "cronjob"
    job = "job"

    @staticmethod
    def from_str(label):
        if label == "deployment":
            return ControllerType.deployment
        if label == "daemonset":
            return ControllerType.daemonset
        if label == "statefulset":
            return ControllerType.statefulset
        if label == "cronjob":
            return ControllerType.cronjob
        if label == "job":
            return ControllerType.job
        raise ValueError(f"Unknown controller type {label} specified")


class Controller(BaseModel):
    # Used to represent top level controllers of a pod
    # Derived from the OwnerReference information in the pod
    # But they may not be the top-level controllers of the pod
    # In the event that they are not the top-level controllers, we go through the OwnerReferences of the intermediary controllers until we find the top-level controller
    # Example:
    # pod "test_pod" is owned by a job named "test_job" and the "test_job" in owned by a cronjob named "test_cronjob"
    # the top-level controller of the "test_pod" is the "test_cronjob"
    type_: ControllerType  # Relates to the field kind in OwnerReference
    name: str
    namespace: str | None


class Pod(BaseModel):
    uid: PodUID
    metadata: MetaData[str]
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

    active: Sequence[JobUID] | None
    last_schedule_time: Timestamp | None
    last_successful_time: Timestamp | None


class CronJob(BaseModel):
    uid: CronJobUID
    metadata: MetaData[str]
    spec: CronJobSpec
    status: CronJobStatus
    pod_uids: Sequence[PodUID]
    job_uids: Sequence[JobUID]


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

    active: int | None
    start_time: Timestamp | None
    completion_time: Timestamp | None
    failed: int | None  # it appears that None is equivalent to 0 failed
    succeeded: int | None
    conditions: Sequence[JobCondition] | None


class Job(BaseModel):
    uid: JobUID
    metadata: MetaData[str]
    status: JobStatus
    pod_uids: Sequence[PodUID]


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
    controller: Optional[bool]  # Optional, since some owner references
    # are user-defined and the controller field can be omitted from the yaml.
    # This model is only intended for parsing. The absence of the controller
    # field can be interpreted as controller=False, but this interpretation is
    # done in _match_controllers, where all the interpretation for owner
    # references happens.
    kind: str
    name: str
    namespace: str | None


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
