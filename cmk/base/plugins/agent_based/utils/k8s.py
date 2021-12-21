#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from dataclasses import dataclass
from typing import Dict, List, Literal, Mapping, NewType, Optional, Sequence, TypedDict, Union

from pydantic import BaseModel
from pydantic.fields import Field

from ..agent_based_api.v1.type_defs import StringTable


def parse_json(string_table: StringTable) -> Dict:
    data = json.loads(string_table[0][0])
    assert isinstance(data, dict)
    return data


class Filesystem(TypedDict):
    capacity: int
    available: int
    inodes: int
    inodes_free: int


def to_filesystem(data: Dict[str, int]) -> Filesystem:
    return {
        "capacity": data["capacity"],
        "available": data["available"],
        "inodes": data["inodes"],
        "inodes_free": data["inodes_free"],
    }


class Interface(TypedDict):
    # Note: since used for Counters only float/int are allowed
    rx_packets: int
    tx_packets: int
    rx_errors: int
    tx_errors: int
    rx_bytes: int
    tx_bytes: int
    rx_dropped: int
    tx_dropped: int


def to_interface(data: Dict[str, int]) -> Interface:
    return {
        "rx_packets": data["rx_packets"],
        "tx_packets": data["tx_packets"],
        "rx_errors": data["rx_errors"],
        "tx_errors": data["tx_errors"],
        "rx_bytes": data["rx_bytes"],
        "tx_bytes": data["tx_bytes"],
        "rx_dropped": data["rx_dropped"],
        "tx_dropped": data["tx_dropped"],
    }


class Section(TypedDict):
    filesystem: Dict[str, List[Filesystem]]
    interfaces: Dict[str, List[Interface]]
    timestamp: float


@dataclass
class Address:
    # k8s_endpoint_info
    hostname: str
    ip: str
    node_name: str


@dataclass
class Port:
    # k8s_endpoint_info
    name: str
    port: int
    protocol: str


@dataclass
class Subset:
    # k8s_endpoint_info
    addresses: List[Address]
    not_ready_addresses: List[Address]
    ports: List[Port]


# agent_kube section schemas --------------------------------- #
# TODO: move schemas to separate file (include reason for double definition)

ContainerName = NewType("ContainerName", str)
PodSequence = Sequence[str]
LabelName = NewType("LabelName", str)
LabelValue = NewType("LabelValue", str)


class Label(BaseModel):
    name: LabelName
    value: LabelValue


Labels = Mapping[LabelName, Label]
CreationTimestamp = NewType("CreationTimestamp", float)
Namespace = NewType("Namespace", str)
PodUID = NewType("PodUID", str)
NodeName = NewType("NodeName", str)

# This information is from the one-page API overview v1.22
# Restart policy for all containers within the pod. Default to Always. More info:
RestartPolicy = Literal["Always", "OnFailure", "Never"]

# This information is from the one-page API overview v1.22
# The Quality of Service (QOS) classification assigned to the pod based on resource requirements.
QosClass = Literal["burstable", "besteffort", "guaranteed"]


class PerformanceMetric(BaseModel):
    value: float  # TODO: introduce NewType
    timestamp: int


class PerformanceContainer(BaseModel):
    name: ContainerName


class NodeCount(BaseModel):
    """section: kube_node_count_v1"""

    worker: int = 0
    control_plane: int = 0


class HealthZ(BaseModel):
    status_code: int
    response: str
    # only set if status_code != 200
    verbose_response: Optional[str]


class KubeletInfo(BaseModel):
    """section: kube_node_kubelet_v1"""

    version: str
    health: HealthZ


class PodInfo(BaseModel):
    """section: kube_pod_info_v1"""

    namespace: Optional[Namespace]
    creation_timestamp: Optional[CreationTimestamp]
    labels: Labels  # used for host labels
    node: Optional[NodeName]  # this is optional, because there may be pods, which are not
    # scheduled on any node (e.g., no node with enough capacity is available).
    qos_class: QosClass
    restart_policy: RestartPolicy
    uid: PodUID


class APIHealth(BaseModel):
    ready: HealthZ
    live: HealthZ


class ClusterInfo(BaseModel):
    """section: kube_cluster_details_v1"""

    api_health: APIHealth


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


class ContainerCount(BaseModel):
    """section: kube_node_container_count_v1"""

    running: int = 0
    waiting: int = 0
    terminated: int = 0


class Memory(BaseModel):
    """section: k8s_live_memory_v1"""

    memory_usage_bytes: float
    memory_swap: float


class NodeInfo(BaseModel):
    """section: kube_node_info_v1"""

    architecture: str
    kernel_version: str
    os_image: str
    labels: Labels


class Resources(BaseModel):
    limit: float = float("inf")
    requests: float = 0.0


class StartTime(BaseModel):
    """section: kube_start_time_v1"""

    start_time: int


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


class ContainerInfo(BaseModel):
    id: Optional[str]  # id of non-ready container is None
    name: str
    image: str
    ready: bool
    state: Union[ContainerTerminatedState, ContainerWaitingState, ContainerRunningState]
    restart_count: int


class DeploymentInfo(BaseModel):
    """section: kube_deployment_info_v1"""

    name: str
    namespace: Namespace
    labels: Labels
    creation_timestamp: CreationTimestamp
    images: Sequence[str]
    containers: Sequence[str]


class PodContainers(BaseModel):
    """section: kube_pod_containers_v1"""

    containers: Mapping[str, ContainerInfo]
