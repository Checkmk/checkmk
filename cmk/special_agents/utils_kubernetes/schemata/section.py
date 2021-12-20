#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
The schemas contained in this file are used to serialize data in the agent output.

This file should not contain any code and should not import from anywhere
except the python standard library or pydantic.
"""
import enum
from typing import Literal, Mapping, NewType, Optional, Sequence, Union

from pydantic import BaseModel

from cmk.special_agents.utils_kubernetes.schemata import api

ContainerName = NewType("ContainerName", str)
PodSequence = Sequence[str]


class PerformanceMetric(BaseModel):
    value: float
    timestamp: float


class PerformanceContainer(BaseModel):
    name: ContainerName


class ExceptionalResource(str, enum.Enum):
    """
    Kubernetes allows omitting the limits and/or requests field for a container. This enum allows us
    to take this into account, when aggregating containers accross a Kubernetes object.
    """

    unspecified = "unspecified"
    """
    We return this value if there is at least one container, where the limit/request was omitted.
    """
    zero = "zero"
    # Kubernetes allows setting the limit field of a container to zero. According to this issue,
    # https://github.com/kubernetes/kubernetes/issues/86244
    # this means the container with limit 0 has unlimited resources. Our understanding is that this
    # is connected to the behaviour of Docker: Kubernetes passes the Docker runtime the limit value.
    # Docker then assigns all the memory on the host machine. It therefore means that github issues
    # might be inaccurate: If there is a container runtime, which uses the limit differently, then
    # the cluster may behave differently.
    """
    Because limit=0 means unlimited rather than zero, we cannot simply add a limit of 0.
    We return this value if there is at least one container, where the limit field was set to zero.
    """
    zero_unspecified = "zero_unspecified"
    """
    If both of the above conditions apply to a limit, we use this value.
    """


AggregatedLimit = Union[ExceptionalResource, float]
AggregatedRequest = Union[Literal[ExceptionalResource.unspecified], float]


class Resources(BaseModel):
    request: AggregatedRequest
    limit: AggregatedLimit


class PodInfo(BaseModel):
    """section: kube_pod_info_v1"""

    namespace: Optional[api.Namespace]
    creation_timestamp: Optional[api.CreationTimestamp]
    labels: api.Labels  # used for host labels
    node: Optional[api.NodeName]  # this is optional, because there may be pods, which are not
    # scheduled on any node (e.g., no node with enough capacity is available).
    qos_class: api.QosClass
    restart_policy: api.RestartPolicy
    uid: api.PodUID


class PodResources(BaseModel):
    """section: kube_pod_resources_v1"""

    running: PodSequence = []
    pending: PodSequence = []
    succeeded: PodSequence = []
    failed: PodSequence = []
    unknown: PodSequence = []


class PodResourcesWithCapacity(PodResources):
    """section: kube_pod_resources_with_capacity_v1"""

    capacity: int
    allocatable: int


class PodLifeCycle(BaseModel):
    """section: kube_pod_lifecycle_v1"""

    phase: api.Phase


class PodCondition(BaseModel):
    status: bool
    reason: Optional[str]
    detail: Optional[str]
    last_transition_time: Optional[int]


class PodConditions(BaseModel):
    """section: k8s_pod_conditions_v1"""

    initialized: Optional[PodCondition]
    scheduled: PodCondition
    containersready: Optional[PodCondition]
    ready: Optional[PodCondition]


class PodContainers(BaseModel):
    """section: kube_pod_containers_v1"""

    containers: Mapping[str, api.ContainerInfo]


class NodeCount(BaseModel):
    """section: kube_node_count_v1"""

    worker: int = 0
    control_plane: int = 0


class NodeInfo(api.NodeInfo):
    """section: kube_node_info_v1"""

    labels: api.Labels


class DeploymentInfo(BaseModel):
    """section: kube_deployment_info_v1"""

    name: str
    namespace: api.Namespace
    labels: api.Labels
    creation_timestamp: api.CreationTimestamp
    images: Sequence[str]
    containers: Sequence[str]


class DeploymentConditions(BaseModel):
    """section: kube_deployment_conditions_v1"""

    conditions: Sequence[api.DeploymentCondition]


class ContainerCount(BaseModel):
    """section: kube_node_container_count_v1"""

    running: int = 0
    waiting: int = 0
    terminated: int = 0


class ContainerCpuUsage(PerformanceContainer):
    cpu_usage_seconds_total: PerformanceMetric


class CpuUsage(BaseModel):
    """section: k8s_live_cpu_usage_v1"""

    usage: float


class Memory(BaseModel):
    """section: k8s_live_memory_v1"""

    memory_usage_bytes: float
