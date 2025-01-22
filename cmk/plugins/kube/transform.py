#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This file contains helper functions to convert kubernetes specific
data structures to version independent data structured defined in schemata.api
"""

from __future__ import annotations

import typing
from collections.abc import Iterable, Mapping, Sequence
from typing import cast, Literal, TypeAlias, TypeVar

import pydantic
from kubernetes.client import (  # type: ignore[attr-defined]
    # https://github.com/kubernetes-client/python/issues/2033
    V1Container,
    V1ContainerStatus,
    V1CronJob,
    V1CronJobSpec,
    V1CronJobStatus,
    V1DaemonSet,
    V1DaemonSetSpec,
    V1DaemonSetStatus,
    V1Deployment,
    V1DeploymentSpec,
    V1DeploymentStatus,
    V1Job,
    V1JobCondition,
    V1JobStatus,
    V1LabelSelector,
    V1LabelSelectorRequirement,
    V1Namespace,
    V1ObjectMeta,
    V1PersistentVolumeClaim,
    V1Pod,
    V1PodCondition,
    V1PodSpec,
    V1ReplicaSet,
    V1ReplicationController,
    V1ResourceQuota,
    V1ResourceQuotaSpec,
    V1ScopeSelector,
    V1StatefulSet,
)

from . import transform_json
from .schemata import api
from .schemata.api import convert_to_timestamp, parse_cpu_cores, parse_resource_value
from .transform_any import parse_match_labels


def parse_metadata_no_namespace(metadata: V1ObjectMeta) -> api.MetaDataNoNamespace:
    return api.MetaDataNoNamespace.model_validate(metadata)


def parse_metadata(metadata: V1ObjectMeta) -> api.MetaData:
    return api.MetaData.model_validate(metadata)


def container_resources(container: V1Container) -> api.ContainerResources:
    parsed_limits = api.ResourcesRequirements()
    parsed_requests = api.ResourcesRequirements()
    if container.resources is not None:
        if limits := container.resources.limits:
            parsed_limits = api.ResourcesRequirements(
                memory=parse_resource_value(limits["memory"]) if "memory" in limits else None,
                cpu=parse_cpu_cores(limits["cpu"]) if "cpu" in limits else None,
            )
        if requests := container.resources.requests:
            parsed_requests = api.ResourcesRequirements(
                memory=parse_resource_value(requests["memory"]) if "memory" in requests else None,
                cpu=parse_cpu_cores(requests["cpu"]) if "cpu" in requests else None,
            )

    return api.ContainerResources(
        limits=parsed_limits,
        requests=parsed_requests,
    )


def containers_spec(containers: Sequence[V1Container]) -> Sequence[api.ContainerSpec]:
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


def pod_spec(pod: V1Pod) -> api.PodSpec:
    spec: V1PodSpec = expect_value(pod.spec)

    def _parse_obj_as(
        model: type[list[T]], expr: typing.Sequence[T] | None
    ) -> typing.Sequence[T] | None:
        adapter = pydantic.TypeAdapter(model)
        return adapter.validate_python(expr)

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
        volumes=_parse_obj_as(list[api.Volume], spec.volumes) if spec.volumes else None,
    )


def pod_status(pod: V1Pod) -> api.PodStatus:
    start_time: float | None
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
    container_statuses: Sequence[V1ContainerStatus] | None,
) -> dict[str, api.ContainerStatus]:
    result: dict[str, api.ContainerStatus] = {}
    if container_statuses is None:
        return {}
    for status in container_statuses:
        state: api.ContainerTerminatedState | api.ContainerRunningState | api.ContainerWaitingState
        if (details := status.state.terminated) is not None:
            state = api.ContainerTerminatedState(
                exit_code=details.exit_code,
                start_time=(
                    int(convert_to_timestamp(details.started_at))
                    if details.started_at is not None
                    else None
                ),
                end_time=(
                    int(convert_to_timestamp(details.finished_at))
                    if details.finished_at is not None
                    else None
                ),
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
    conditions: Sequence[V1PodCondition],
) -> list[api.PodCondition]:
    condition_types = {
        "PodHasNetwork": api.ConditionType.PODHASNETWORK,
        "PodReadyToStartContainers": api.ConditionType.PODREADYTOSTARTCONTAINERS,
        "PodScheduled": api.ConditionType.PODSCHEDULED,
        "Initialized": api.ConditionType.INITIALIZED,
        "ContainersReady": api.ConditionType.CONTAINERSREADY,
        "Ready": api.ConditionType.READY,
        "DisruptionTarget": api.ConditionType.DISRUPTIONTARGET,
    }
    result = []
    for condition in conditions:
        pod_condition = {
            "status": condition.status,
            "reason": condition.reason,
            "detail": condition.message,
            "last_transition_time": (
                int(convert_to_timestamp(condition.last_transition_time))
                if condition.last_transition_time
                else None
            ),
        }
        if condition.type in condition_types:
            pod_condition["type"] = condition_types[condition.type]
        else:
            pod_condition["custom_type"] = condition.type

        result.append(api.PodCondition(**pod_condition))
    return result


def deployment_replicas(status: V1DeploymentStatus, spec: V1DeploymentSpec) -> api.Replicas:
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
    status: V1DeploymentStatus,
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


def pod_from_client(pod: V1Pod, controllers: Sequence[api.Controller]) -> api.Pod:
    return api.Pod(
        uid=api.PodUID(pod.metadata.uid),
        metadata=parse_metadata(pod.metadata),
        status=pod_status(pod),
        spec=pod_spec(pod),
        containers=pod_containers(pod.status.container_statuses),
        init_containers=pod_containers(pod.status.init_container_statuses),
        controllers=controllers,
    )


def parse_match_expressions(
    match_expressions: Iterable[V1LabelSelectorRequirement] | None,
) -> api.MatchExpressions:
    return [
        api.MatchExpression(
            key=api.LabelName(expression.key),
            operator=cast(Literal["In", "NotIn", "Exists", "DoesNotExist"], expression.operator),
            values=[api.LabelValue(v) for v in expression.values or []],
        )
        for expression in (match_expressions or [])
    ]


def parse_selector(selector: V1LabelSelector) -> api.Selector:
    return api.Selector(
        match_labels=parse_match_labels(selector.match_labels or {}),
        match_expressions=parse_match_expressions(selector.match_expressions),
    )


def parse_deployment_spec(deployment_spec: V1DeploymentSpec) -> api.DeploymentSpec:
    if deployment_spec.strategy.type == "Recreate":
        return api.DeploymentSpec(
            min_ready_seconds=deployment_spec.min_ready_seconds or 0,
            strategy=api.Recreate(),
            selector=parse_selector(deployment_spec.selector),
        )
    if deployment_spec.strategy.type == "RollingUpdate":
        return api.DeploymentSpec(
            min_ready_seconds=deployment_spec.min_ready_seconds or 0,
            strategy=api.RollingUpdate(
                max_surge=deployment_spec.strategy.rolling_update.max_surge,
                max_unavailable=deployment_spec.strategy.rolling_update.max_unavailable,
            ),
            selector=parse_selector(deployment_spec.selector),
        )
    raise ValueError(f"Unknown strategy type: {deployment_spec.strategy.type}")


def deployment_from_client(
    deployment: V1Deployment, pod_uids: Sequence[api.PodUID]
) -> api.Deployment:
    return api.Deployment(
        metadata=parse_metadata(deployment.metadata),
        spec=parse_deployment_spec(deployment.spec),
        status=api.DeploymentStatus(
            conditions=deployment_conditions(deployment.status),
            replicas=deployment_replicas(deployment.status, deployment.spec),
        ),
        pods=pod_uids,
    )


def parse_cron_job_spec(spec: V1CronJobSpec) -> api.CronJobSpec:
    return api.CronJobSpec(
        concurrency_policy=api.ConcurrencyPolicy(spec.concurrency_policy),
        schedule=spec.schedule,
        successful_jobs_history_limit=spec.successful_jobs_history_limit,
        failed_jobs_history_limit=spec.failed_jobs_history_limit,
        suspend=spec.suspend,
    )


def parse_cron_job_status(status: V1CronJobStatus) -> api.CronJobStatus:
    return api.CronJobStatus(
        active=[ref.uid for ref in status.active] if status.active is not None else None,
        last_successful_time=(
            convert_to_timestamp(status.last_successful_time)
            if status.last_successful_time is not None
            else None
        ),
        last_schedule_time=(
            convert_to_timestamp(status.last_schedule_time)
            if status.last_schedule_time is not None
            else None
        ),
    )


def cron_job_from_client(
    cron_job: V1CronJob,
    pod_uids: Sequence[api.PodUID],
    job_uids: Sequence[api.JobUID],
) -> api.CronJob:
    return api.CronJob(
        uid=api.CronJobUID(cron_job.metadata.uid),
        metadata=parse_metadata(cron_job.metadata),
        spec=parse_cron_job_spec(cron_job.spec),
        status=parse_cron_job_status(cron_job.status),
        pod_uids=pod_uids,
        job_uids=job_uids,
    )


def parse_job_status(status: V1JobStatus) -> api.JobStatus:
    return api.JobStatus(
        active=status.active,
        start_time=convert_to_timestamp(status.start_time) if status.start_time else None,
        completion_time=(
            convert_to_timestamp(status.completion_time) if status.completion_time else None
        ),
        failed=status.failed,
        succeeded=status.succeeded,
        conditions=_parse_and_remove_duplicate_conditions(status.conditions),
    )


def _parse_and_remove_duplicate_conditions(
    conditions: Sequence[V1JobCondition] | None,
) -> Sequence[api.JobCondition]:
    """Parse and remove duplicate job conditions

    Note:
        For Kubernetes < 1.25, in some cases the API reports duplicate conditions, we want to
        filter these out before they are handled on the check. This has been resolved in 1.25
        https://github.com/kubernetes/kubernetes/issues/109904

    """
    if conditions is None:
        return []

    def _parse_job_condition(condition: V1JobCondition) -> api.JobCondition:
        return api.JobCondition(
            type_=api.JobConditionType(condition.type.capitalize()),
            status=api.ConditionStatus(condition.status.capitalize()),
        )

    def _condition_identifier(condition: V1JobCondition) -> str:
        return f"{condition.type}-{condition.last_probe_time}"

    parsed_conditions: dict[str, api.JobCondition] = {}

    for job_condition in conditions:
        parsed_conditions.setdefault(
            _condition_identifier(job_condition), _parse_job_condition(job_condition)
        )

    return list(parsed_conditions.values())


def job_from_client(
    job: V1Job,
    pod_uids: Sequence[api.PodUID],
) -> api.Job:
    return api.Job(
        uid=api.JobUID(job.metadata.uid),
        metadata=parse_metadata(job.metadata),
        status=parse_job_status(job.status),
        pod_uids=pod_uids,
    )


def parse_daemonset_status(status: V1DaemonSetStatus) -> api.DaemonSetStatus:
    return api.DaemonSetStatus(
        desired_number_scheduled=status.desired_number_scheduled,
        updated_number_scheduled=status.updated_number_scheduled or 0,
        number_misscheduled=status.number_misscheduled,
        number_ready=status.number_ready,
        number_available=status.number_available or 0,
    )


def parse_daemonset_spec(daemonset_spec: V1DaemonSetSpec) -> api.DaemonSetSpec:
    if daemonset_spec.update_strategy.type == "OnDelete":
        return api.DaemonSetSpec(
            min_ready_seconds=daemonset_spec.min_ready_seconds or 0,
            strategy=api.OnDelete(),
            selector=parse_selector(daemonset_spec.selector),
        )
    if daemonset_spec.update_strategy.type == "RollingUpdate":
        return api.DaemonSetSpec(
            min_ready_seconds=daemonset_spec.min_ready_seconds or 0,
            strategy=api.RollingUpdate(
                max_surge=daemonset_spec.update_strategy.rolling_update.max_surge,
                max_unavailable=daemonset_spec.update_strategy.rolling_update.max_unavailable,
            ),
            selector=parse_selector(daemonset_spec.selector),
        )
    raise ValueError(f"Unknown strategy type: {daemonset_spec.update_strategy.type}")


def daemonset_from_client(daemonset: V1DaemonSet, pod_uids: Sequence[api.PodUID]) -> api.DaemonSet:
    return api.DaemonSet(
        metadata=parse_metadata(daemonset.metadata),
        spec=parse_daemonset_spec(daemonset.spec),
        status=parse_daemonset_status(status=daemonset.status),
        pods=pod_uids,
    )


def namespace_from_client(namespace: V1Namespace) -> api.Namespace:
    return api.Namespace.model_validate(namespace)


def parse_resource_quota_spec(
    spec: V1ResourceQuotaSpec,
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
        hard=(
            api.HardRequirement(
                memory=parse_resource_requirement("memory", spec.hard),
                cpu=parse_resource_requirement("cpu", spec.hard),
            )
            if spec.hard is not None
            else None
        ),
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
            parse_cpu_cores(value) if resource == "cpu" else parse_resource_value(value)
        )

    if not requirements:
        return None
    return api.HardResourceRequirement(**requirements)


def parse_scope_selector(
    scope_selector: V1ScopeSelector | None,
) -> api.ScopeSelector | None:
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
    resource_quota: V1ResourceQuota,
) -> api.ResourceQuota | None:
    """Parse Kubernetes resource quota client object

    * Resource quotas which include the CrossNamespacePodAffinity scope
    are currently not supported and treated as non existent
    """
    try:
        spec = parse_resource_quota_spec(resource_quota.spec)
    except NotImplementedError:
        return None

    return api.ResourceQuota(
        metadata=parse_metadata(resource_quota.metadata),
        spec=spec,
    )


def persistent_volume_claim_from_client(
    persistent_volume_claim: V1PersistentVolumeClaim,
) -> api.PersistentVolumeClaim:
    return api.PersistentVolumeClaim(
        metadata=parse_metadata(persistent_volume_claim.metadata),
        spec=api.PersistentVolumeClaimSpec.model_validate(persistent_volume_claim.spec),
        status=api.PersistentVolumeClaimStatus.model_validate(persistent_volume_claim.status),
    )


WorkloadResource: TypeAlias = (
    V1Pod
    | V1Deployment
    | V1ReplicaSet
    | V1DaemonSet
    | V1Job
    | V1CronJob
    | V1ReplicationController
    | V1StatefulSet
)


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
