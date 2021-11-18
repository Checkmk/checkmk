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
from collections import defaultdict
from typing import Dict, List, NewType, Optional, Sequence, Union

from kubernetes import client  # type: ignore[import] # pylint: disable=import-error

from .schemata import api

Labels = NewType("Labels", Dict[str, str])


def parse_frac_prefix(value: str) -> float:
    if value.endswith("m"):
        return 0.001 * float(value[:-1])
    return float(value)


def parse_memory(value: str) -> float:
    if value.endswith("Ki"):
        return 1024 ** 1 * float(value[:-2])
    if value.endswith("Mi"):
        return 1024 ** 2 * float(value[:-2])
    if value.endswith("Gi"):
        return 1024 ** 3 * float(value[:-2])
    if value.endswith("Ti"):
        return 1024 ** 4 * float(value[:-2])
    if value.endswith("Pi"):
        return 1024 ** 5 * float(value[:-2])
    if value.endswith("Ei"):
        return 1024 ** 6 * float(value[:-2])

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


def parse_metadata(metadata: client.V1ObjectMeta, labels=None) -> api.MetaData:
    if not labels:
        labels = metadata.labels if metadata.labels else {}

    return api.MetaData(
        name=metadata.name,
        namespace=metadata.namespace,
        creation_timestamp=convert_to_timestamp(metadata.creation_timestamp),
        labels=labels,
    )


def parse_pod_info(pod: client.V1Pod) -> api.PodSpec:
    info = {}
    if pod.spec:
        info.update({"node": pod.spec.node_name, "host_network": pod.spec.host_network})

    if pod.status:
        info.update(
            {
                "host_ip": pod.status.host_ip,
                "pod_ip": pod.status.pod_ip,
                "qos_class": pod.status.qos_class.lower(),
            }
        )
    return api.PodSpec(**info)


def pod_resources(pod: client.V1Pod) -> api.PodUsageResources:
    memory: Dict[str, float] = defaultdict(float)
    cpu: Dict[str, float] = defaultdict(float)

    for container in pod.spec.containers:
        resources = container.resources
        if not resources:
            continue

        if resources.limits:
            memory["limit"] += parse_memory(resources.limits.get("memory", "inf"))
            cpu["limit"] += parse_frac_prefix(resources.limits.get("cpu", "inf"))
        else:
            memory["limit"] += float("inf")
            cpu["limit"] += float("inf")

        if resources.requests:
            cpu["requests"] += parse_frac_prefix(resources.requests.get("cpu", "0.0"))
            memory["requests"] += parse_memory(resources.requests.get("memory", "0.0"))

    return api.PodUsageResources(cpu=api.Resources(**cpu), memory=api.Resources(**memory))


def pod_containers(pod: client.V1Pod) -> List[api.ContainerInfo]:
    container_statuses: List[client.V1ContainerStatus] = (
        [] if pod.status.container_statuses is None else pod.status.container_statuses
    )
    result: List[api.ContainerInfo] = []
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

        result.append(
            api.ContainerInfo(
                id=status.container_id,
                name=status.name,
                image=status.image,
                ready=status.ready,
                state=state,
                restart_count=status.restart_count,
            )
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
        }
        if condition.type in condition_types:
            pod_condition["type"] = condition_types[condition.type]
        else:
            pod_condition["custom_type"] = condition.type

        result.append(api.PodCondition(**pod_condition))
    return result


def is_control_plane(labels: Optional[Labels]) -> bool:
    return labels is not None and (
        # 1.18 returns an empty string, 1.20 returns 'true'
        "node-role.kubernetes.io/master" in labels
        or "node-role.kubernetes.io/control-plane" in labels
    )


def node_conditions(node: client.V1Node) -> Optional[api.NodeStatus]:
    if not node.status:
        return None
    conditions = node.status.conditions
    if not conditions:
        return None
    return api.NodeStatus(**{c.type: bool(c.status) for c in conditions})


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


def pod_from_client(pod: client.V1Pod) -> api.Pod:
    return api.Pod(
        uid=pod.metadata.uid,
        metadata=parse_metadata(pod.metadata),
        status=api.PodStatus(
            conditions=pod_conditions(pod.status.conditions),
            phase=api.Phase(pod.status.phase.lower()),
            start_time=int(convert_to_timestamp(pod.status.start_time)),
        ),
        spec=parse_pod_info(pod),
        resources=pod_resources(pod),
        containers=pod_containers(pod),
    )


def node_from_client(node: client.V1Node, kubelet_health: api.HealthZ) -> api.Node:
    return api.Node(
        metadata=parse_metadata(node.metadata),
        conditions=node_conditions(node),
        resources=parse_node_resources(node),
        control_plane=is_control_plane(node.metadata.labels),
        kubelet_info=api.KubeletInfo(
            version=node.status.node_info.kubelet_version,
            health=kubelet_health,
        ),
    )


def deployment_from_client(
    deployment: client.V1Deployment, pod_uids=Sequence[api.PodUID]
) -> api.Deployment:
    return api.Deployment(
        metadata=parse_metadata(deployment.metadata),
        pods=pod_uids,
    )
