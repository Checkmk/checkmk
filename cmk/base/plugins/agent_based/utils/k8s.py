#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from dataclasses import dataclass
from typing import Dict, List, Optional, TypedDict

from pydantic import BaseModel

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


class NodeCount(BaseModel):
    """section: k8s_node_count_v1"""

    worker: int = 0
    control_plane: int = 0


class HealthZ(BaseModel):
    status_code: int
    response: str
    # only set if status_code != 200
    verbose_response: Optional[str]


class KubeletInfo(BaseModel):
    """section: k8s_node_kubelet_v1"""

    version: str
    health: HealthZ


class APIHealth(BaseModel):
    ready: HealthZ
    live: HealthZ


class ClusterInfo(BaseModel):
    """section: k8s_cluster_details_v1"""

    api_health: APIHealth


class PodResources(BaseModel):
    """section: k8s_pods_resources"""

    running: int = 0
    pending: int = 0
    succeeded: int = 0
    failed: int = 0
    unknown: int = 0
    capacity: Optional[int] = None
    allocatable: Optional[int] = None


class ContainerCount(BaseModel):
    """section: k8s_node_container_count_v1"""

    running: int = 0
    waiting: int = 0
    terminated: int = 0
