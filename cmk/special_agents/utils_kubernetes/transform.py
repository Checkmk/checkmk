#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This file contains helper functions to convert kubernetes specific
data structures to version independent data structured defined in schemata.api
"""

from __future__ import annotations

from typing import cast, Dict, Iterable, List, Literal, Mapping, Optional, Sequence, TypeVar, Union

from kubernetes import client  # type: ignore[import]

from . import transform_json
from .schemata import api
from .schemata.api import Label, LabelName
from .transform_any import convert_to_timestamp, parse_annotations, parse_labels, parse_match_labels


def parse_frac_prefix(value: str) -> float:
    """Parses the string `value` with a suffix of 'm' or 'k' into a float.

    Examples:
       >>> parse_frac_prefix("359m")
       0.359
       >>> parse_frac_prefix("4k")
       4000.0
    """

    if value.endswith("m"):
        return 0.001 * float(value[:-1])
    if value.endswith("k"):
        return 1e3 * float(value[:-1])
    return float(value)


def parse_memory(value: str) -> float:  # pylint: disable=too-many-branches
    if value.endswith("Ki"):
        return 1024**1 * float(value[:-2])
    if value.endswith("Mi"):
        return 1024**2 * float(value[:-2])
    if value.endswith("Gi"):
        return 1024**3 * float(value[:-2])
    if value.endswith("Ti"):
        return 1024**4 * float(value[:-2])
    if value.endswith("Pi"):
        return 1024**5 * float(value[:-2])
    if value.endswith("Ei"):
        return 1024**6 * float(value[:-2])

    if value.endswith("K") or value.endswith("k"):
        return 1e3 * float(value[:-1])
    if value.endswith("M"):
        return 1e6 * float(value[:-1])
    if value.endswith("G"):
        return 1e9 * float(value[:-1])
    if value.endswith("T"):
        return 1e12 * float(value[:-1])
    if value.endswith("P"):
        return 1e15 * float(value[:-1])
    if value.endswith("E"):
        return 1e18 * float(value[:-1])

    # millibytes are a useless, but valid option:
    # https://github.com/kubernetes/kubernetes/issues/28741
    if value.endswith("m"):
        return 1e-3 * float(value[:-1])

    return float(value)


def parse_metadata_no_namespace(
    metadata: client.V1ObjectMeta, type_: type[api.ObjectName]
) -> api.MetaDataNoNamespace[api.ObjectName]:
    return api.MetaDataNoNamespace(
        name=type_(metadata.name),
        creation_timestamp=convert_to_timestamp(metadata.creation_timestamp),
        labels=parse_labels(metadata.labels),
        annotations=parse_annotations(metadata.annotations),
    )


def parse_metadata(
    metadata: client.V1ObjectMeta, type_: type[api.ObjectName]
) -> api.MetaData[api.ObjectName]:
    metadata_no_namespace = parse_metadata_no_namespace(metadata, type_=type_)
    return api.MetaData(
        name=type_(metadata_no_namespace.name),
        namespace=api.NamespaceName(metadata.namespace),
        creation_timestamp=metadata_no_namespace.creation_timestamp,
        labels=metadata_no_namespace.labels,
        annotations=metadata_no_namespace.annotations,
    )


def container_resources(container: client.V1Container) -> api.ContainerResources:
    parsed_limits = api.ResourcesRequirements()
    parsed_requests = api.ResourcesRequirements()
    if container.resources is not None:
        if limits := container.resources.limits:
            parsed_limits = api.ResourcesRequirements(
                memory=parse_memory(limits["memory"]) if "memory" in limits else None,
                cpu=parse_frac_prefix(limits["cpu"]) if "cpu" in limits else None,
            )
        if requests := container.resources.requests:
            parsed_requests = api.ResourcesRequirements(
                memory=parse_memory(requests["memory"]) if "memory" in requests else None,
                cpu=parse_frac_prefix(requests["cpu"]) if "cpu" in requests else None,
            )

    return api.ContainerResources(
        limits=parsed_limits,
        requests=parsed_requests,
    )


def containers_spec(containers: Sequence[client.V1Container]) -> Sequence[api.ContainerSpec]:
    return [
        api.ContainerSpec(
            name=container.name,
            resources=container_resources(container),
            image_pull_policy=container.image_pull_policy,
        )
        for container in containers
    ]


T = TypeVar("T")


def expect_value(v: T | None) -> T:
    if v is None:
        raise NotImplementedError("Unexpected missing value.")
    return v


def pod_spec(pod: client.V1Pod) -> api.PodSpec:
    spec: client.V1PodSpec = expect_value(pod.spec)
    return api.PodSpec(
        node=spec.node_name,
        host_network=spec.host_network,
        dns_policy=spec.dns_policy,
        restart_policy=spec.restart_policy,
        containers=containers_spec(spec.containers),
        init_containers=containers_spec(
            spec.init_containers if spec.init_containers is not None else []
        ),
        priority_class_name=spec.priority_class_name,
        active_deadline_seconds=spec.active_deadline_seconds,
    )


def pod_status(pod: client.V1Pod) -> api.PodStatus:
    start_time: Optional[float]
    if pod.status.start_time is not None:
        start_time = convert_to_timestamp(pod.status.start_time)
    else:
        start_time = None

    return api.PodStatus(
        conditions=pod_conditions(pod.status.conditions) if pod.status.conditions else None,
        phase=api.Phase(pod.status.phase.lower()),
        start_time=api.Timestamp(start_time) if start_time else None,
        host_ip=api.IpAddress(pod.status.host_ip) if pod.status.host_ip else None,
        pod_ip=api.IpAddress(pod.status.pod_ip) if pod.status.pod_ip else None,
        qos_class=pod.status.qos_class.lower() if pod.status.qos_class else None,
    )


def pod_containers(
    container_statuses: Optional[Sequence[client.V1ContainerStatus]],
) -> Dict[str, api.ContainerStatus]:
    result: Dict[str, api.ContainerStatus] = {}
    if container_statuses is None:
        return {}
    for status in container_statuses:
        state: Union[
            api.ContainerTerminatedState, api.ContainerRunningState, api.ContainerWaitingState
        ]
        if (details := status.state.terminated) is not None:
            state = api.ContainerTerminatedState(
                exit_code=details.exit_code,
                start_time=int(convert_to_timestamp(details.started_at))
                if details.started_at is not None
                else None,
                end_time=int(convert_to_timestamp(details.finished_at))
                if details.finished_at is not None
                else None,
                reason=details.reason,
                detail=details.message,
            )
        elif (details := status.state.running) is not None:
            state = api.ContainerRunningState(
                start_time=int(convert_to_timestamp(details.started_at)),
            )
        elif (details := status.state.waiting) is not None:
            state = api.ContainerWaitingState(
                reason=details.reason,
                detail=details.message,
            )
        else:
            raise AssertionError(f"Unknown container state {status.state}")

        result[status.name] = api.ContainerStatus(
            container_id=status.container_id,
            image_id=status.image_id,
            name=status.name,
            image=status.image,
            ready=status.ready,
            state=state,
            restart_count=status.restart_count,
        )
    return result


def pod_conditions(
    conditions: Sequence[client.V1PodCondition],
) -> List[api.PodCondition]:
    condition_types = {
        "PodScheduled": api.ConditionType.PODSCHEDULED,
        "Initialized": api.ConditionType.INITIALIZED,
        "ContainersReady": api.ConditionType.CONTAINERSREADY,
        "Ready": api.ConditionType.READY,
    }
    result = []
    for condition in conditions:
        pod_condition = {
            "status": condition.status,
            "reason": condition.reason,
            "detail": condition.message,
            "last_transition_time": int(convert_to_timestamp(condition.last_transition_time)),
        }
        if condition.type in condition_types:
            pod_condition["type"] = condition_types[condition.type]
        else:
            pod_condition["custom_type"] = condition.type

        result.append(api.PodCondition(**pod_condition))
    return result


def _give_root_if_prefix_present(label: LabelName, prefix: str) -> Optional[str]:
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


def parse_node_roles(labels: Optional[Mapping[LabelName, Label]]) -> Sequence[str]:
    if labels is None:
        return []
    return [
        role
        for label in labels
        if (role := _give_root_if_prefix_present(label, "node-role.kubernetes.io/")) is not None
    ]


def node_conditions(status: client.V1NodeStatus) -> Optional[Sequence[api.NodeCondition]]:
    conditions = status.conditions
    if not conditions:
        return None
    return [
        api.NodeCondition(
            status=c.status,
            type_=c.type,
            reason=c.reason,
            detail=c.message,
            last_transition_time=int(convert_to_timestamp(c.last_transition_time)),
        )
        for c in conditions
    ]


def node_info(node: client.V1Node) -> api.NodeInfo:
    return api.NodeInfo(
        architecture=node.status.node_info.architecture,
        kernel_version=node.status.node_info.kernel_version,
        os_image=node.status.node_info.os_image,
        operating_system=node.status.node_info.operating_system,
        container_runtime_version=node.status.node_info.container_runtime_version,
    )


def parse_node_resources(node: client.V1Node) -> Dict[str, api.NodeResources]:
    if node.status:
        capacity = node.status.capacity
        allocatable = node.status.allocatable
    else:
        capacity, allocatable = None, None

    return node_resources(capacity, allocatable)


def node_resources(  # type:ignore[no-untyped-def]
    capacity, allocatable
) -> Dict[str, api.NodeResources]:
    resources = {
        "capacity": api.NodeResources(),
        "allocatable": api.NodeResources(),
    }

    if not capacity and not allocatable:
        return resources

    if capacity:
        resources["capacity"] = api.NodeResources(
            cpu=parse_frac_prefix(capacity.get("cpu", 0.0)),
            memory=parse_memory(capacity.get("memory", 0.0)),
            pods=capacity.get("pods", 0),
        )
    if allocatable:
        resources["allocatable"] = api.NodeResources(
            cpu=parse_frac_prefix(allocatable.get("cpu", 0.0)),
            memory=parse_memory(allocatable.get("memory", 0.0)),
            pods=allocatable.get("pods", 0),
        )
    return resources


def deployment_replicas(
    status: client.V1DeploymentStatus, spec: client.V1DeploymentSpec
) -> api.Replicas:
    # A deployment always has at least 1 replica. It is not possible to deploy
    # a deployment that has 0 replicas. On the other hand, it is possible to have
    # 0 available/unavailable/updated/ready replicas. This is shown as 'null'
    # (i.e. None) in the source data, but the interpretation is that the number
    # of the replicas in this case is 0.
    # Under certain conditions, the status.replicas can report a 'null' value, therefore
    # the spec.replicas is taken as base value since this reflects the desired value
    return api.Replicas(
        replicas=spec.replicas,
        available=status.available_replicas or 0,
        unavailable=status.unavailable_replicas or 0,
        updated=status.updated_replicas or 0,
        ready=status.ready_replicas or 0,
    )


def deployment_conditions(
    status: client.V1DeploymentStatus,
) -> Mapping[str, api.DeploymentCondition]:
    return {
        condition.type.lower(): api.DeploymentCondition(
            status=condition.status,
            last_transition_time=convert_to_timestamp(condition.last_transition_time),
            reason=condition.reason,
            message=condition.message,
        )
        for condition in status.conditions or []
    }


def pod_from_client(pod: client.V1Pod, controllers: Sequence[api.Controller]) -> api.Pod:
    return api.Pod(
        uid=api.PodUID(pod.metadata.uid),
        metadata=parse_metadata(pod.metadata, str),
        status=pod_status(pod),
        spec=pod_spec(pod),
        containers=pod_containers(pod.status.container_statuses),
        init_containers=pod_containers(pod.status.init_container_statuses),
        controllers=controllers,
    )


def node_addresses_from_client(
    node_addresses: Optional[Sequence[client.V1NodeAdresses]],
) -> api.NodeAddresses:
    if not node_addresses:
        return []
    return [
        api.NodeAddress(
            address=address.address,
            type_=address.type,
        )
        for address in node_addresses
    ]


def node_from_client(node: client.V1Node, kubelet_health: api.HealthZ) -> api.Node:
    metadata = parse_metadata_no_namespace(node.metadata, api.NodeName)
    return api.Node(
        metadata=metadata,
        status=api.NodeStatus(
            conditions=node_conditions(node.status),
            node_info=node_info(node),
            addresses=node_addresses_from_client(node.status.addresses),
        ),
        resources=parse_node_resources(node),
        roles=parse_node_roles(metadata.labels),
        kubelet_info=api.KubeletInfo(
            version=node.status.node_info.kubelet_version,
            proxy_version=node.status.node_info.kube_proxy_version,
            health=kubelet_health,
        ),
    )


def parse_match_expressions(
    match_expressions: Iterable[client.V1LabelSelectorRequirement] | None,
) -> api.MatchExpressions:
    return [
        api.MatchExpression(
            key=api.LabelName(expression.key),
            operator=cast(Literal["In", "NotIn", "Exists", "DoesNotExist"], expression.operator),
            values=[api.LabelValue(v) for v in expression.values or []],
        )
        for expression in (match_expressions or [])
    ]


def parse_selector(selector: client.V1LabelSelector) -> api.Selector:
    return api.Selector(
        match_labels=parse_match_labels(selector.match_labels or {}),
        match_expressions=parse_match_expressions(selector.match_expressions),
    )


def parse_deployment_spec(deployment_spec: client.V1DeploymentSpec) -> api.DeploymentSpec:
    if deployment_spec.strategy.type == "Recreate":
        return api.DeploymentSpec(
            strategy=api.Recreate(),
            selector=parse_selector(deployment_spec.selector),
        )
    if deployment_spec.strategy.type == "RollingUpdate":
        return api.DeploymentSpec(
            strategy=api.RollingUpdate(
                max_surge=deployment_spec.strategy.rolling_update.max_surge,
                max_unavailable=deployment_spec.strategy.rolling_update.max_unavailable,
            ),
            selector=parse_selector(deployment_spec.selector),
        )
    raise ValueError(f"Unknown strategy type: {deployment_spec.strategy.type}")


def deployment_from_client(
    deployment: client.V1Deployment, pod_uids: Sequence[api.PodUID]
) -> api.Deployment:
    return api.Deployment(
        metadata=parse_metadata(deployment.metadata, str),
        spec=parse_deployment_spec(deployment.spec),
        status=api.DeploymentStatus(
            conditions=deployment_conditions(deployment.status),
            replicas=deployment_replicas(deployment.status, deployment.spec),
        ),
        pods=pod_uids,
    )


def parse_cron_job_spec(spec: client.V1CronJobSpec) -> api.CronJobSpec:
    return api.CronJobSpec(
        concurrency_policy=api.ConcurrencyPolicy(spec.concurrency_policy),
        schedule=spec.schedule,
        successful_jobs_history_limit=spec.successful_jobs_history_limit,
        failed_jobs_history_limit=spec.failed_jobs_history_limit,
        suspend=spec.suspend,
    )


def parse_cron_job_status(status: client.V1CronJobStatus) -> api.CronJobStatus:
    return api.CronJobStatus(
        active=[ref.uid for ref in status.active] if status.active is not None else None,
        last_successful_time=convert_to_timestamp(status.last_successful_time)
        if status.last_successful_time is not None
        else None,
        last_schedule_time=convert_to_timestamp(status.last_schedule_time),
    )


def cron_job_from_client(
    cron_job: client.V1CronJob,
    pod_uids: Sequence[api.PodUID],
    job_uids: Sequence[api.JobUID],
) -> api.CronJob:
    return api.CronJob(
        uid=api.CronJobUID(cron_job.metadata.uid),
        metadata=parse_metadata(cron_job.metadata, str),
        spec=parse_cron_job_spec(cron_job.spec),
        status=parse_cron_job_status(cron_job.status),
        pod_uids=pod_uids,
        job_uids=job_uids,
    )


def parse_job_status(status: client.V1JobStatus) -> api.JobStatus:
    def _parse_job_condition(condition: client.V1JobCondition) -> api.JobCondition:
        return api.JobCondition(
            type_=api.JobConditionType(condition.type.capitalize()),
            status=api.ConditionStatus(condition.status.capitalize()),
        )

    return api.JobStatus(
        active=status.active,
        start_time=convert_to_timestamp(status.start_time) if status.start_time else None,
        completion_time=convert_to_timestamp(status.completion_time)
        if status.completion_time
        else None,
        failed=status.failed,
        succeeded=status.succeeded,
        conditions=[_parse_job_condition(condition) for condition in status.conditions]
        if status.conditions is not None
        else [],
    )


def job_from_client(
    job: client.V1Job,
    pod_uids: Sequence[api.PodUID],
) -> api.Job:
    return api.Job(
        uid=api.JobUID(job.metadata.uid),
        metadata=parse_metadata(job.metadata, str),
        status=parse_job_status(job.status),
        pod_uids=pod_uids,
    )


def parse_daemonset_status(status: client.V1DaemonSetStatus) -> api.DaemonSetStatus:
    return api.DaemonSetStatus(
        desired_number_scheduled=status.desired_number_scheduled,
        updated_number_scheduled=status.updated_number_scheduled or 0,
        number_misscheduled=status.number_misscheduled,
        number_ready=status.number_ready,
        number_available=status.number_available or 0,
    )


def parse_daemonset_spec(daemonset_spec: client.V1DaemonSetSpec) -> api.DaemonSetSpec:
    if daemonset_spec.update_strategy.type == "OnDelete":
        return api.DaemonSetSpec(
            strategy=api.OnDelete(),
            selector=parse_selector(daemonset_spec.selector),
        )
    if daemonset_spec.update_strategy.type == "RollingUpdate":
        return api.DaemonSetSpec(
            strategy=api.RollingUpdate(
                max_surge=daemonset_spec.update_strategy.rolling_update.max_surge,
                max_unavailable=daemonset_spec.update_strategy.rolling_update.max_unavailable,
            ),
            selector=parse_selector(daemonset_spec.selector),
        )
    raise ValueError(f"Unknown strategy type: {daemonset_spec.update_strategy.type}")


def daemonset_from_client(
    daemonset: client.V1DaemonSet, pod_uids: Sequence[api.PodUID]
) -> api.DaemonSet:
    return api.DaemonSet(
        metadata=parse_metadata(daemonset.metadata, str),
        spec=parse_daemonset_spec(daemonset.spec),
        status=parse_daemonset_status(status=daemonset.status),
        pods=pod_uids,
    )


def parse_statefulset_status(status: client.V1StatefulSetStatus) -> api.StatefulSetStatus:
    return api.StatefulSetStatus(
        ready_replicas=status.ready_replicas or 0,
        updated_replicas=status.updated_replicas or 0,
    )


def parse_statefulset_spec(statefulset_spec: client.V1StatefulSetSpec) -> api.StatefulSetSpec:
    if statefulset_spec.update_strategy.type == "OnDelete":
        return api.StatefulSetSpec(
            strategy=api.OnDelete(),
            selector=parse_selector(statefulset_spec.selector),
            replicas=statefulset_spec.replicas,
        )
    if statefulset_spec.update_strategy.type == "RollingUpdate":
        partition = (
            rolling_update.partition
            if (rolling_update := statefulset_spec.update_strategy.rolling_update)
            else 0
        )
        return api.StatefulSetSpec(
            strategy=api.StatefulSetRollingUpdate(partition=partition),
            selector=parse_selector(statefulset_spec.selector),
            replicas=statefulset_spec.replicas,
        )
    raise ValueError(f"Unknown strategy type: {statefulset_spec.update_strategy.type}")


def statefulset_from_client(
    statefulset: client.V1StatefulSet, pod_uids: Sequence[api.PodUID]
) -> api.StatefulSet:
    return api.StatefulSet(
        metadata=parse_metadata(statefulset.metadata, str),
        spec=parse_statefulset_spec(statefulset.spec),
        status=parse_statefulset_status(statefulset.status),
        pods=pod_uids,
    )


def namespace_from_client(namespace: client.V1Namespace) -> api.Namespace:
    return api.Namespace(
        metadata=parse_metadata_no_namespace(namespace.metadata, api.NamespaceName),
    )


def parse_resource_quota_spec(
    spec: client.V1ResourceQuotaSpec,
) -> api.ResourceQuotaSpec:
    # TODO: CMK-10288 add validation logic
    try:
        scope_selector = parse_scope_selector(spec.scope_selector)
        scopes = (
            [api.QuotaScope(scope) for scope in spec.scopes] if spec.scopes is not None else None
        )
    except ValueError:
        raise NotImplementedError("At least one of the given scopes is not supported")

    return api.ResourceQuotaSpec(
        hard=api.HardRequirement(
            memory=parse_resource_requirement("memory", spec.hard),
            cpu=parse_resource_requirement("cpu", spec.hard),
        )
        if spec.hard is not None
        else None,
        scope_selector=scope_selector,
        scopes=scopes,
    )


def parse_resource_requirement(
    resource: Literal["memory", "cpu"], hard: Mapping[str, str]
) -> api.HardResourceRequirement | None:
    # request & limit are only defined once for each requirement. It is possible to double
    # define them in the yaml file but only one value is taken into account.
    requirements = {}
    for requirement, value in hard.items():
        if resource not in requirement:
            continue
        requirement_type = "limit" if "limits" in requirement else "request"
        requirements[requirement_type] = (
            parse_frac_prefix(value) if resource == "cpu" else parse_memory(value)
        )

    if not requirements:
        return None
    return api.HardResourceRequirement(**requirements)


def parse_scope_selector(
    scope_selector: Optional[client.V1ScopeSelector],
) -> Optional[api.ScopeSelector]:
    if scope_selector is None:
        return None
    return api.ScopeSelector(
        match_expressions=[
            api.ScopedResourceMatchExpression(
                operator=match_expression.operator,
                scope_name=match_expression.scope_name,
                values=match_expression.values,
            )
            for match_expression in scope_selector.match_expressions
        ]
    )


def resource_quota_from_client(
    resource_quota: client.V1ResourceQuota,
) -> Optional[api.ResourceQuota]:
    """Parse Kubernetes resource quota client object

    * Resource quotas which include the CrossNamespacePodAffinity scope
    are currently not supported and treated as non existent
    """
    try:
        spec = parse_resource_quota_spec(resource_quota.spec)
    except NotImplementedError:
        return None

    return api.ResourceQuota(
        metadata=parse_metadata(resource_quota.metadata, str),
        spec=spec,
    )


WorkloadResource = Union[
    client.V1Deployment,
    client.V1ReplicaSet,
    client.V1DaemonSet,
    client.V1Job,
    client.V1CronJob,
    client.V1ReplicationController,
    client.V1StatefulSet,
]


def dependent_object_owner_refererences_from_client(
    dependent: WorkloadResource,
) -> api.OwnerReferences:
    return [
        api.OwnerReference(
            uid=ref.uid,
            controller=ref.controller,
            kind=ref.kind,
            name=ref.name,
            namespace=dependent.metadata.namespace,
        )
        for ref in dependent.metadata.owner_references or []
    ]


def parse_object_to_owners(
    workload_resources_client: Iterable[WorkloadResource],
    workload_resources_json: Iterable[transform_json.JSONStatefulSet],
) -> Mapping[str, api.OwnerReferences]:
    return {
        workload_resource.metadata.uid: dependent_object_owner_refererences_from_client(
            dependent=workload_resource
        )
        for workload_resource in workload_resources_client
    } | {
        transform_json.dependent_object_uid_from_json(
            workload_resource
        ): transform_json.dependent_object_owner_refererences_from_json(workload_resource)
        for workload_resource in workload_resources_json
    }
