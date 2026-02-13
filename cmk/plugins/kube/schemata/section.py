#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
The schemas contained in this file are used to serialize data in the agent output.

This file should not contain any code and should not import from anywhere
except the python standard library or pydantic.
"""

import enum
import json
from collections.abc import Mapping, Sequence
from typing import assert_never, Literal, NewType

import requests
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from cmk.plugins.kube import prometheus_api, query
from cmk.plugins.kube.schemata import api

HostName = NewType("HostName", str)
PodSequence = Sequence[str]
NodeName = NewType("NodeName", str)
OsName = NewType("OsName", str)
PythonCompiler = NewType("PythonCompiler", str)
Version = NewType("Version", str)

FilteredAnnotations = NewType("FilteredAnnotations", api.Annotations)
""" Annotations filtered with user input.

After receiving the annotations from the Kubernetes API, we cannot process all
of them as HostLabels. FilteredAnnotations are those annotations, which can be
processed. This means that the annotations can no longer be arbitrary json
objects and that options from the `Kubernetes` rule have been taken into account.
"""


class Section(BaseModel):
    model_config = ConfigDict(frozen=True)


class PerformanceMetric(BaseModel):
    value: float
    timestamp: float


class PerformanceContainer(BaseModel):
    name: api.ContainerName


class BasePodLifeCycle(BaseModel):
    phase: api.Phase


class CollectorState(enum.Enum):
    OK = "ok"
    ERROR = "error"


class CollectorHandlerLog(BaseModel):
    status: CollectorState
    title: str
    detail: str | None = None


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
    cadvisor_version: Version | None = None
    checkmk_agent_version: Version | None = None


class NamespaceInfo(Section):
    """section: kube_namespace_info_v1"""

    name: api.NamespaceName
    creation_timestamp: api.Timestamp | None = None
    labels: api.Labels
    annotations: FilteredAnnotations
    cluster: str
    kubernetes_cluster_hostname: str


class CronJobInfo(Section):
    """section: kube_cron_job_info_v1"""

    name: str
    namespace: api.NamespaceName
    creation_timestamp: api.Timestamp | None = None
    labels: api.Labels
    annotations: FilteredAnnotations
    schedule: str
    concurrency_policy: api.ConcurrencyPolicy
    failed_jobs_history_limit: int
    successful_jobs_history_limit: int
    suspend: bool
    cluster: str
    kubernetes_cluster_hostname: str


class CronJobStatus(Section):
    """section: kube_cron_job_status_v1"""

    active_jobs_count: int | None = None
    last_duration: float | None = None  # duration of the last completed job
    last_successful_time: api.Timestamp | None = None
    last_schedule_time: api.Timestamp | None = None


class JobStatus(BaseModel):
    conditions: Sequence[api.JobCondition]
    start_time: api.Timestamp | None = None
    completion_time: api.Timestamp | None = None


class JobPod(BaseModel):
    init_containers: Mapping[str, api.ContainerStatus]
    containers: Mapping[str, api.ContainerStatus]
    lifecycle: BasePodLifeCycle


class CronJobLatestJob(Section):
    """section: kube_cron_job_latest_job_v1"""

    status: JobStatus
    pods: Sequence[JobPod]


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


class CollectorComponentsMetadata(Section):
    """section: kube_collector_metadata_v1"""

    processing_log: CollectorHandlerLog
    cluster_collector: ClusterCollectorMetadata | None = None
    nodes: Sequence[NodeMetadata] | None = None


class CollectorProcessingLogs(Section):
    """section: kube_collector_processing_logs_v1"""

    container: CollectorHandlerLog
    machine: CollectorHandlerLog


# TODO: Resources is a bad name, this should be changed to something like Requirements. When
# choosing a name, other section BaseModel names like AllocatableResource and PerformanceUsage
# be taken into account
class Resources(Section):
    """sections: "[kube_memory_resources_v1, kube_cpu_resources_v1]"""

    request: float
    limit: float
    count_unspecified_requests: int
    count_unspecified_limits: int
    count_zeroed_limits: int
    count_total: int


class AllocatableResource(Section):
    """sections: [kube_allocatable_cpu_resource_v1, kube_allocatable_memory_resource_v1]"""

    context: Literal["cluster", "node"]
    value: float


class Controller(BaseModel):
    type_: str
    name: str


# A sequence of controllers, e.g. deployment -> replica set. For two adjacent elements, the first
# one controls the second one. The final element controls the pod (but this is not implemented yet).
# Control chains may be incomplete.
ControlChain = Sequence[Controller]


class PodInfo(Section):
    """section: kube_pod_info_v1"""

    namespace: api.NamespaceName | None = None
    name: str
    creation_timestamp: api.Timestamp | None = None
    labels: api.Labels  # used for host labels
    annotations: FilteredAnnotations  # used for host labels
    node: api.NodeName | None = None  # this is optional, because there may be pods, which are not
    # scheduled on any node (e.g., no node with enough capacity is available).
    host_network: bool | None = None
    dns_policy: str | None = None
    host_ip: api.IpAddress | None = None
    pod_ip: api.IpAddress | None = None
    qos_class: api.QosClass | None = None  # can be None, if the Pod was evicted.
    restart_policy: api.RestartPolicy
    uid: api.PodUID
    # TODO: see CMK-9901
    controllers: ControlChain = []
    cluster: str
    kubernetes_cluster_hostname: str


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


class PodLifeCycle(BasePodLifeCycle, Section):
    """section: kube_pod_lifecycle_v1"""


class PodCondition(BaseModel):
    status: bool
    reason: str | None = Field(None)
    detail: str | None = Field(None)
    last_transition_time: int | None = Field(None)


class PodConditions(Section):
    """section: kube_pod_conditions_v1"""

    initialized: PodCondition | None = Field(None)
    hasnetwork: PodCondition | None = Field(None)
    readytostartcontainers: PodCondition | None = Field(None)
    scheduled: PodCondition
    containersready: PodCondition | None = Field(None)
    ready: PodCondition | None = Field(None)
    disruptiontarget: PodCondition | None = Field(None)


class PodContainers(Section):
    """section: kube_pod_containers_v1"""

    containers: Mapping[str, api.ContainerStatus]


class ContainerSpec(BaseModel):
    image_pull_policy: api.ImagePullPolicy


class ContainerSpecs(Section):
    """section: kube_pod_container_specs_v1"""

    containers: Mapping[api.ContainerName, ContainerSpec]


class ThinContainers(BaseModel):
    """ThinContainers reduces agent ouput duplication.

    Container information is often times duplicated across different piggyback hosts. In order
    to reduce the amount of duplication, we maintain this data structure, which is based on a smaller
    subset of fields. This structure can then be used with hosts such as Deployment, which only
    require a small amount of container-related information.
    """

    images: frozenset[str]
    names: Sequence[api.ContainerName]


class CountableNode(BaseModel):
    ready: bool
    roles: Sequence[str]


class NodeCount(Section):
    """section: kube_node_count_v1"""

    nodes: Sequence[CountableNode]


class NodeInfo(Section):
    """section: kube_node_info_v1"""

    # NodeSystemInfo
    architecture: str
    kernel_version: str
    os_image: str
    operating_system: str
    container_runtime_version: str
    # ObjectMeta
    name: api.NodeName
    creation_timestamp: api.Timestamp
    labels: api.Labels
    annotations: FilteredAnnotations
    addresses: api.NodeAddresses
    cluster: str
    kubernetes_cluster_hostname: str


class NodeCondition(BaseModel, extra="forbid"):
    type_: str
    status: api.NodeConditionStatus
    reason: str | None
    message: str | None


class NodeConditions(Section):
    """section: kube_node_conditions_v2"""

    conditions: Sequence[NodeCondition]


class DeploymentInfo(Section):
    """section: kube_deployment_info_v1"""

    name: str
    namespace: api.NamespaceName
    labels: api.Labels
    annotations: FilteredAnnotations
    selector: api.Selector
    creation_timestamp: api.Timestamp
    containers: ThinContainers
    cluster: str
    kubernetes_cluster_hostname: str


class DaemonSetInfo(Section):
    """section: kube_daemonset_info_v1"""

    name: str
    namespace: api.NamespaceName
    labels: api.Labels
    annotations: FilteredAnnotations
    selector: api.Selector
    creation_timestamp: api.Timestamp
    containers: ThinContainers
    cluster: str
    kubernetes_cluster_hostname: str


class StatefulSetInfo(Section):
    """section: kube_statefulset_info_v1"""

    name: str
    namespace: api.NamespaceName
    labels: api.Labels
    annotations: FilteredAnnotations
    selector: api.Selector
    creation_timestamp: api.Timestamp
    containers: ThinContainers
    cluster: str
    kubernetes_cluster_hostname: str


class DeploymentConditions(Section):
    """section: kube_deployment_conditions_v1"""

    available: api.DeploymentCondition | None = None
    progressing: api.DeploymentCondition | None = None
    replicafailure: api.DeploymentCondition | None = None


class ContainerCount(Section):
    """section: kube_node_container_count_v1"""

    running: int = 0
    waiting: int = 0
    terminated: int = 0


DisplayableStrategy = api.OnDelete | api.Recreate | api.RollingUpdate | api.StatefulSetRollingUpdate


class UpdateStrategy(Section):
    """section: kube_update_strategy_v1"""

    strategy: DisplayableStrategy = Field(discriminator="type_")


class ControllerSpec(Section):
    """section: kube_controller_spec_v1"""

    min_ready_seconds: int


class Memory(BaseModel):
    type_: Literal["memory"] = Field("memory")
    usage: float


class Cpu(BaseModel):
    type_: Literal["cpu"] = Field("cpu")
    usage: float


class AttachedVolume(BaseModel):
    """The PV from a kubelet metrics representation"""

    capacity: float
    free: float
    persistent_volume_claim: str
    namespace: api.NamespaceName


class PerformanceUsage(Section):
    """section: [kube_performance_cpu_v1, kube_performance_memory_v1]"""

    resource: Cpu | Memory = Field(discriminator="type_")


class ClusterInfo(Section):
    """section: kube_cluster_info_v1"""

    name: str
    version: api.GitVersion


class ClusterDetails(Section):
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

    machine: NodeCollectorReplica | None = None
    container: NodeCollectorReplica | None = None
    errors: IdentificationError


class StartTime(Section):
    """section: kube_start_time_v1"""

    start_time: api.Timestamp


class KubeletInfo(Section):
    """section: kube_node_kubelet_v1"""

    version: str
    proxy_version: str
    health: api.HealthZ | api.NodeConnectionError


class HardResourceRequirement(Section, api.HardResourceRequirement):
    """sections: [kube_resource_quota_memory_v1, kube_resource_quota_cpu_v1]"""


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
    details: str | None = None

    @classmethod
    def from_response(cls, response: query.HTTPResponse) -> "PrometheusResult":
        query_, result = response
        type_, details = cls._from_result(result)
        return cls(query_=query_, type_=type_, details=details)

    @classmethod
    def _from_result(cls, result: query.HTTPResult) -> tuple[ResultType, str | None]:
        match result:
            case requests.exceptions.RequestException():
                return ResultType.request_exception, type(result).__name__
            case json.JSONDecodeError():
                return ResultType.json_decode_error, None
            case ValidationError():
                return ResultType.validation_error, None
            case prometheus_api.ResponseError():
                return ResultType.response_error, f"{result.error_type}: {result.error}"
            case prometheus_api.ResponseSuccess(data=prometheus_api.Vector(result=[])):
                return ResultType.response_empty_result, None
            case prometheus_api.ResponseSuccess(data=prometheus_api.Vector()):
                return ResultType.success, None
            case prometheus_api.ResponseSuccess():
                return ResultType.response_invalid_data, None
        assert_never(result)

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


class StorageRequirement(BaseModel):
    storage: int


class PersistentVolumeClaimStatus(BaseModel):
    phase: api.PersistentVolumeClaimPhase | None = None
    capacity: StorageRequirement | None = None


class PersistentVolumeClaimMetaData(BaseModel):
    name: str
    namespace: api.NamespaceName


class PersistentVolumeClaim(BaseModel):
    metadata: PersistentVolumeClaimMetaData
    status: PersistentVolumeClaimStatus
    volume_name: str | None = None


class PersistentVolumeClaims(Section):
    """section: kube_pvc_v1"""

    claims: Mapping[str, PersistentVolumeClaim]


class PersistentVolumeClaimAttachedVolumes(Section):
    """section: kube_pvc_volumes_v1"""

    volumes: Mapping[str, AttachedVolume]


class PersistentVolume(BaseModel):
    name: str
    spec: api.PersistentVolumeSpec


class AttachedPersistentVolumes(Section):
    """section: kube_pvc_pvs_v1"""

    volumes: Mapping[str, PersistentVolume]
