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
from typing import Mapping, NewType, Optional, Sequence

from pydantic import BaseModel

from cmk.special_agents.utils_kubernetes.schemata import api

ContainerName = NewType("ContainerName", str)
PodSequence = Sequence[str]


class PerformanceMetric(BaseModel):
    value: float
    timestamp: float


class PerformanceContainer(BaseModel):
    name: ContainerName


class CollectorState(enum.Enum):
    OK = "ok"
    ERROR = "error"


class CollectorLog(BaseModel):
    component: str
    status: CollectorState
    message: str
    detail: Optional[str]


class CollectorLogs(BaseModel):
    """section: kube_collector_connection_v1"""

    logs: Sequence[CollectorLog]


class Resources(BaseModel):
    """sections: "[kube_memory_resources_v1, kube_cpu_resources_v1]"""

    request: float
    limit: float
    count_unspecified_requests: int
    count_unspecified_limits: int
    count_zeroed_limits: int
    count_total: int


class AllocatableResource(BaseModel):
    """sections: [kube_allocatable_cpu_resource_v1, kube_allocatable_memory_resource_v1]"""

    value: float


class ControllerType(enum.Enum):
    deployment = "deployment"

    @staticmethod
    def from_str(label):
        if label == "deployment":
            return ControllerType.deployment
        raise ValueError(f"Unknown controller type {label} specified")


class Controller(BaseModel):
    type_: ControllerType
    name: str


class PodInfo(BaseModel):
    """section: kube_pod_info_v1"""

    namespace: Optional[api.Namespace]
    name: str
    creation_timestamp: Optional[api.CreationTimestamp]
    labels: api.Labels  # used for host labels
    node: Optional[api.NodeName]  # this is optional, because there may be pods, which are not
    # scheduled on any node (e.g., no node with enough capacity is available).
    host_network: Optional[str]
    dns_policy: Optional[str]
    host_ip: Optional[api.IpAddress]
    pod_ip: Optional[api.IpAddress]
    qos_class: api.QosClass
    restart_policy: api.RestartPolicy
    uid: api.PodUID
    controllers: Sequence[Controller] = []


class PodResources(BaseModel):
    """section: kube_pod_resources_v1"""

    running: PodSequence = []
    pending: PodSequence = []
    succeeded: PodSequence = []
    failed: PodSequence = []
    unknown: PodSequence = []


class AllocatablePods(BaseModel):
    """section: kube_allocatable_pods_v1"""

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


class ContainerSpec(BaseModel):
    name: ContainerName
    image_pull_policy: api.ImagePullPolicy


class ContainerSpecs(BaseModel):
    """section: kube_pod_container_specs_v1"""

    containers: Mapping[ContainerName, ContainerSpec]


class ReadyCount(BaseModel):
    ready: int = 0
    not_ready: int = 0

    @property
    def total(self) -> int:
        return self.ready + self.not_ready


class NodeCount(BaseModel):
    """section: kube_node_count_v1"""

    worker: ReadyCount = ReadyCount()
    control_plane: ReadyCount = ReadyCount()


class NodeInfo(api.NodeInfo):
    """section: kube_node_info_v1"""

    name: api.NodeName
    creation_timestamp: api.CreationTimestamp
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

    available: Optional[api.DeploymentCondition]
    progressing: Optional[api.DeploymentCondition]
    replicafailure: Optional[api.DeploymentCondition]


class ContainerCount(BaseModel):
    """section: kube_node_container_count_v1"""

    running: int = 0
    waiting: int = 0
    terminated: int = 0


class ContainerCpuUsage(PerformanceContainer):
    cpu_usage_seconds_total: PerformanceMetric


class CpuUsage(BaseModel):
    """section: kube_performance_cpu_usage_v1"""

    usage: float


class Memory(BaseModel):
    """section: kube_performance_memory_v1"""

    memory_usage_bytes: float  # TODO: change naming
