#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
This file contains helper functions to convert kubernetes specific
data structures to version independent data structured defined in schemata.api
"""

from __future__ import annotations

import datetime
import time
from typing import Dict, List, Mapping, Optional, Sequence, Type, Union

from kubernetes import client  # type: ignore[import] # pylint: disable=import-error

from .schemata import api
from .schemata.api import Label, LabelName, LabelValue


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


def parse_memory(value: str) -> float:
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


# TODO: change to Timestamp type
def convert_to_timestamp(k8s_date_time: Union[str, datetime.datetime]) -> float:
    if isinstance(k8s_date_time, str):
        date_time = datetime.datetime.strptime(k8s_date_time, "%Y-%m-%dT%H:%M:%SZ")
    elif isinstance(k8s_date_time, datetime.datetime):
        date_time = k8s_date_time
    else:
        raise TypeError(
            f"Can not convert to timestamp: '{k8s_date_time}' of type {type(k8s_date_time)}"
        )
    return time.mktime(date_time.timetuple())


def parse_labels(labels: Mapping[str, str]) -> Optional[Mapping[LabelName, Label]]:
    if labels is None:
        return None
    return {LabelName(k): Label(name=LabelName(k), value=LabelValue(v)) for k, v in labels.items()}


def parse_metadata(
    metadata: client.V1ObjectMeta, model: Type[api.MetaData] = api.MetaData
) -> api.MetaData:
    return model(
        name=metadata.name,
        namespace=metadata.namespace,
        creation_timestamp=convert_to_timestamp(metadata.creation_timestamp),
        labels=parse_labels(metadata.labels),
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


def pod_spec(pod: client.V1Pod) -> api.PodSpec:
    if not pod.spec:
        return api.PodSpec()

    return api.PodSpec(
        node=pod.spec.node_name,
        host_network=pod.spec.host_network,
        dns_policy=pod.spec.dns_policy,
        restart_policy=pod.spec.restart_policy,
        containers=containers_spec(pod.spec.containers),
        init_containers=containers_spec(
            pod.spec.init_containers if pod.spec.init_containers is not None else []
        ),
    )


def pod_status(pod: client.V1Pod) -> api.PodStatus:
    start_time: Optional[float]
    if pod.status.start_time is not None:
        start_time = convert_to_timestamp(pod.status.start_time)
    else:
        start_time = None

    return api.PodStatus(
        conditions=pod_conditions(pod.status.conditions),
        phase=api.Phase(pod.status.phase.lower()),
        start_time=api.Timestamp(start_time) if start_time else None,
        host_ip=api.IpAddress(pod.status.host_ip) if pod.status.host_ip else None,
        pod_ip=api.IpAddress(pod.status.pod_ip) if pod.status.pod_ip else None,
        qos_class=pod.status.qos_class.lower(),
    )


def pod_containers(
    container_statuses: Optional[Sequence[client.V1ContainerStatus]],
) -> Dict[str, api.ContainerInfo]:
    result: Dict[str, api.ContainerInfo] = {}
    if container_statuses is None:
        return {}
    for status in container_statuses:
        state: Union[
            api.ContainerTerminatedState, api.ContainerRunningState, api.ContainerWaitingState
        ]
        if (details := status.state.terminated) is not None:
            state = api.ContainerTerminatedState(
                type="terminated",
                exit_code=details.exit_code,
                start_time=int(convert_to_timestamp(details.started_at)),
                end_time=int(convert_to_timestamp(details.finished_at)),
                reason=details.reason,
                detail=details.message,
            )
        elif (details := status.state.running) is not None:
            state = api.ContainerRunningState(
                type="running",
                start_time=int(convert_to_timestamp(details.started_at)),
            )
        elif (details := status.state.waiting) is not None:
            state = api.ContainerWaitingState(
                type="waiting",
                reason=details.reason,
                detail=details.message,
            )
        else:
            raise AssertionError(f"Unknown container state {status.state}")

        result[status.name] = api.ContainerInfo(
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


def is_control_plane(labels: Optional[Mapping[LabelName, Label]]) -> bool:
    return labels is not None and (
        # 1.18 returns an empty string, 1.20 returns 'true'
        "node-role.kubernetes.io/master" in labels
        or "node-role.kubernetes.io/control-plane" in labels
    )


def node_conditions(status: client.V1Status) -> Optional[Sequence[api.NodeCondition]]:
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


def node_resources(capacity, allocatable) -> Dict[str, api.NodeResources]:
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


def deployment_replicas(status: client.V1DeploymentStatus) -> api.Replicas:
    # A deployment always has at least 1 replica. It is not possible to deploy
    # a deployment that has 0 replicas. On the other hand, it is possible to have
    # 0 available/unavailable/updated/ready replicas. This is shown as 'null'
    # (i.e. None) in the source data, but the interpretation is that the number
    # of the replicas in this case is 0.
    return api.Replicas(
        replicas=status.replicas,
        available=status.available_replicas or 0,
        unavailable=status.unavailable_replicas or 0,
        updated=status.updated_replicas or 0,
        ready=status.ready_replicas or 0,
    )


def deployment_conditions(
    status: client.V1DeploymentStatus,
) -> Mapping[str, api.DeploymentCondition]:
    conditions = {}
    for condition in status.conditions:
        conditions[condition.type.lower()] = api.DeploymentCondition(
            status=condition.status,
            last_transition_time=convert_to_timestamp(condition.last_transition_time),
            reason=condition.reason,
            message=condition.message,
        )
    return conditions


def pod_from_client(pod: client.V1Pod) -> api.Pod:
    return api.Pod(
        uid=api.PodUID(pod.metadata.uid),
        metadata=parse_metadata(pod.metadata, model=api.PodMetaData),
        status=pod_status(pod),
        spec=pod_spec(pod),
        containers=pod_containers(pod.status.container_statuses),
        init_containers=pod_containers(pod.status.init_container_statuses),
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
    metadata = parse_metadata(node.metadata)
    return api.Node(
        metadata=metadata,
        status=api.NodeStatus(
            conditions=node_conditions(node.status),
            node_info=node_info(node),
            addresses=node_addresses_from_client(node.status.addresses),
        ),
        resources=parse_node_resources(node),
        control_plane=is_control_plane(metadata.labels),
        kubelet_info=api.KubeletInfo(
            version=node.status.node_info.kubelet_version,
            proxy_version=node.status.node_info.kube_proxy_version,
            health=kubelet_health,
        ),
    )


def parse_selector(selector: client.V1LabelSelector) -> api.Selector:
    match_expressions = selector.match_expressions or []
    return api.Selector(
        match_labels=selector.match_labels or {},
        match_expressions=[expression.to_dict() for expression in match_expressions],
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
    deployment: client.V1Deployment, pod_uids=Sequence[api.PodUID]
) -> api.Deployment:
    return api.Deployment(
        metadata=parse_metadata(deployment.metadata),
        spec=parse_deployment_spec(deployment.spec),
        status=api.DeploymentStatus(
            conditions=deployment_conditions(deployment.status),
            replicas=deployment_replicas(deployment.status),
        ),
        pods=pod_uids,
    )


def parse_cron_job_spec(spec: client.V1CronJobSpec) -> api.CronJobSpec:
    return api.CronJobSpec(
        concurrency_policy=api.ConcurrencyPolicy(spec.concurrency_policy), schedule=spec.schedule
    )


def cron_job_from_client(
    cron_job: client.V1CronJob,
    pod_uids: Sequence[api.PodUID],
) -> api.CronJob:
    return api.CronJob(
        uid=api.CronJobUID(cron_job.metadata.uid),
        metadata=parse_metadata(cron_job.metadata),
        spec=parse_cron_job_spec(cron_job.spec),
        pod_uids=pod_uids,
    )
