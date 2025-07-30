from datetime import datetime
from enum import StrEnum
from uuid import UUID
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict


class TaskType(StrEnum):
    SNMP_DISCOVERY = "SNMP_DISCOVERY"
    CONFIG = "CONFIG"
    NETWORK_CHECK = "NETWORK_CHECK"
    HOST_CHECK = "HOST_CHECK"
    SERVICE_CHECK_FORCE = "SERVICE_CHECK_FORCE"


class TaskRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: UUID
    type: TaskType
    payload: Optional[Dict[str, Any]] = None
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
    result_payload: Optional[Dict[str, Any]] = None
    creation_timestamp: datetime
    update_timestamp: datetime
