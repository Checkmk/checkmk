#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class TaskType(StrEnum):
    RELAY_CONFIG = "RELAY_CONFIG"
    FETCH_AD_HOC = "FETCH_AD_HOC"


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"


class ResultType(StrEnum):
    OK = "OK"
    ERROR = "ERROR"


class TaskCreateRequest(BaseModel, frozen=True):
    type: TaskType
    payload: str
    version: int = 1
    timeout: float = Field(
        title="Fetcher timeout",
        description="Fetcher timeout for tasks in seconds",
        default=60.0,
        ge=0,
    )


class TaskCreateResponse(BaseModel, frozen=True):
    task_id: str


class TaskResponse(TaskCreateRequest):
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


# TODO: In this package we should define a RELAY_CONFIG payload that would be used from the relay and the agent receiver to configure the relay
# class RelayConfigPayload(BaseModel):
#     number_of_fetchers: int = Field(..., description="Number of fetchers in the relay")
