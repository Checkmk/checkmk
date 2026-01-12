#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import Base64Bytes, BaseModel, Field


class HEADERS(StrEnum):
    SERIAL = "X-CMK-SERIAL"
    VERSION = "X-CMK-VERSION"


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
    tar_data: Base64Bytes = Field(
        title="Base64 encoded tar data",
        description="Base64 encoded tar data containing the configuration files for the relay",
    )
    type: Literal[_TaskType.RELAY_CONFIG] = _TaskType.RELAY_CONFIG


# Only the tasks that can be created via create task API endpoint
TaskCreateRequestSpec = FetchAdHocTask

# Any task that can be stored in the backend
TaskResponseSpec = FetchAdHocTask | RelayConfigTask


class TaskCreateRequest(BaseModel, frozen=True):
    spec: TaskCreateRequestSpec = Field(discriminator="type")
    version: int = 1


class TaskCreateResponse(BaseModel, frozen=True):
    task_id: str


class TaskResponse(BaseModel, frozen=True):
    spec: TaskResponseSpec = Field(discriminator="type")
    status: TaskStatus
    result_type: ResultType | None
    result_payload: str | None
    creation_timestamp: datetime
    update_timestamp: datetime
    id: str
    version: int = 1


class TaskListResponse(BaseModel, frozen=True):
    tasks: list[TaskResponse]


class TaskUpdateRequest(BaseModel, frozen=True):
    result_type: ResultType
    result_payload: str


class UpdateConfigResponse(BaseModel, frozen=True):
    created: Sequence[str]
    pending: Sequence[str]
    failed: Mapping[str, str]
