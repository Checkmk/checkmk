#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class _TaskType(StrEnum):
    RELAY_CONFIG = "RELAY_CONFIG"
    FETCH_AD_HOC = "FETCH_AD_HOC"


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"


class ResultType(StrEnum):
    OK = "OK"
    ERROR = "ERROR"


class FetchAdHocTask(BaseModel):
    payload: str
    timeout: float = Field(
        title="Fetcher timeout",
        description="Fetcher timeout for tasks in seconds",
        default=60.0,
        ge=0,
    )
    type: Literal[_TaskType.FETCH_AD_HOC] = _TaskType.FETCH_AD_HOC


class RelayConfigTask(BaseModel, frozen=True):
    serial: int
    type: Literal[_TaskType.RELAY_CONFIG] = _TaskType.RELAY_CONFIG


TaskSpec = FetchAdHocTask | RelayConfigTask


class TaskCreateRequest(BaseModel, frozen=True):
    spec: TaskSpec = Field(discriminator="type")
    version: int = 1


class TaskCreateResponse(BaseModel, frozen=True):
    task_id: str


class TaskResponse(TaskCreateRequest, frozen=True):
    status: TaskStatus
    result_type: ResultType | None
    result_payload: str | None
    creation_timestamp: datetime
    update_timestamp: datetime
    id: str


class TaskListResponse(BaseModel, frozen=True):
    tasks: list[TaskResponse]


class TaskUpdateRequest(BaseModel, frozen=True):
    result_type: ResultType
    result_payload: str
