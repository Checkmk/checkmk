from datetime import datetime
from enum import StrEnum
from uuid import UUID
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class TaskType(StrEnum):
    RELAY_CONFIG = "RELAY_CONFIG"
    FETCH_AD_HOC = "FETCH_AD_HOC"


class TaskRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: UUID
    type: TaskType
    payload: str
    version: int = 1


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"


class ResultType(StrEnum):
    OK = "OK"
    ERROR = "ERROR"


class TaskResponse(TaskRequest):
    model_config = ConfigDict(frozen=True)
    status: TaskStatus
    result_type: ResultType
    result_payload: str
    creation_timestamp: datetime
    update_timestamp: datetime


# TODO: In this package we should define a RELAY_CONFIG payload that would be used from the relay and the agent receiver to configure the relay
# class RelayConfigPayload(BaseModel):
#     number_of_fetchers: int = Field(..., description="Number of fetchers in the relay")
