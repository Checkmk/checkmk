#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from typing import Literal, Optional, Tuple, Union

from pydantic import BaseModel


class KubernetesError(Exception):
    pass


class CollectorState(enum.Enum):
    OK = "ok"
    ERROR = "error"


class CollectorHandlerLog(BaseModel):
    status: CollectorState
    title: str
    detail: Optional[str]


class CollectorComponents(BaseModel):
    """section: kube_collector_info_v1"""

    container: CollectorHandlerLog
    machine: CollectorHandlerLog


class Phase(str, enum.Enum):
    RUNNING = "running"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class PodLifeCycle(BaseModel):
    """section: kube_pod_lifecycle_v1"""

    phase: Phase


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


class ConditionStatus(str, enum.Enum):
    TRUE = "True"
    FALSE = "False"
    UNKNOWN = "Unknown"


class DeploymentCondition(BaseModel):
    status: ConditionStatus
    last_transition_time: float
    reason: str
    message: str


class DeploymentConditions(BaseModel):
    """section: kube_deployment_conditions_v1"""

    available: Optional[DeploymentCondition]
    progressing: Optional[DeploymentCondition]
    replicafailure: Optional[DeploymentCondition]


VSResultAge = Union[Tuple[Literal["levels"], Tuple[int, int]], Literal["no_levels"]]
