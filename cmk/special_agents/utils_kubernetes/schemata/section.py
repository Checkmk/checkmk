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
from typing import List, Optional

from pydantic import BaseModel

from cmk.special_agents.utils_kubernetes.schemata import api


class PodResources(BaseModel):
    """section: k8s_pods_resources_v1"""

    running: int = 0
    pending: int = 0
    succeeded: int = 0
    failed: int = 0
    unknown: int = 0


class PodResourcesWithCapacity(PodResources):
    """section: k8s_pods_resources_with_capacity_v1"""

    capacity: int
    allocatable: int


class PodCondition(BaseModel):
    status: bool
    reason: Optional[str]
    detail: Optional[str]


class PodConditions(BaseModel):
    """section: k8s_pod_conditions_v1"""

    initialized: Optional[PodCondition]
    scheduled: PodCondition
    containersready: Optional[PodCondition]
    ready: Optional[PodCondition]


class PodContainers(BaseModel):
    """section: k8s_pod_containers_v1"""

    containers: List[api.ContainerInfo]


class NodeCount(BaseModel):
    """section: k8s_node_count_v1"""

    worker: int = 0
    control_plane: int = 0


class ContainerCount(BaseModel):
    """section: k8s_node_container_count_v1"""

    running: int = 0
    waiting: int = 0
    terminated: int = 0


class CpuUsage(BaseModel):
    """section: k8s_live_cpu_usage_v1"""

    cpu_usage_total: int


class CpuLoad(BaseModel):
    """section: k8s_live_cpu_load_v1"""

    cpu_cfs_throttled_time: int
    cpu_load_average: int


class Memory(BaseModel):
    """section: k8s_live_memory_v1"""

    memory_usage: float
    memory_swap: float
