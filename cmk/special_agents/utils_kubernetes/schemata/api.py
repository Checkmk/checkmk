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
GitVersion = NewType("GitVersion", str)


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

CreationTimestamp = NewType("CreationTimestamp", float)
NamespaceName = NewType("NamespaceName", str)
NodeName = NewType("NodeName", str)
IpAddress = NewType("IpAddress", str)


class MetaData(BaseModel):
    name: str
    namespace: Optional[NamespaceName] = None
    creation_timestamp: Optional[CreationTimestamp] = None
    labels: Labels
    annotations: Annotations


class NodeMetaData(MetaData):
    creation_timestamp: CreationTimestamp
    labels: Labels


class PodMetaData(MetaData):
    namespace: NamespaceName


class NamespaceMetaData(BaseModel):
    name: NamespaceName
    labels: Labels
    annotations: Annotations
    creation_timestamp: CreationTimestamp


class Namespace(BaseModel):
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
    """sections: [kube_resource_quota_memory_v1, kube_resource_quota_cpu_v1]"""

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

    metadata: MetaData
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
    metadata: MetaData
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
    metadata: MetaData
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
    priority_class_name: Optional[str] = None
    active_deadline_seconds: Optional[int] = None


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
