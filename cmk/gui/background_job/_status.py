#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import TypedDict

from pydantic import BaseModel

JobId = str


class JobStatusStates:
    INITIALIZED = "initialized"
    RUNNING = "running"
    FINISHED = "finished"
    STOPPED = "stopped"
    EXCEPTION = "exception"


@dataclass
class InitialStatusArgs:
    title: str = "Background job"
    stoppable: bool = True
    deletable: bool = True
    user: str | None = None
    estimated_duration: float | None = None
    logfile_path: str = "~/var/log/web.log"
    lock_wato: bool = False
    # Only used by ServiceDiscoveryBackgroundJob
    host_name: str = ""


class JobLogInfo(TypedDict):
    JobProgressUpdate: Sequence[str]
    JobResult: Sequence[str]
    JobException: Sequence[str]


class JobStatusSpec(BaseModel):
    state: str  # Make Literal["initialized", "running", "finished", "stopped", "exception"]
    started: float  # Change to Timestamp type later
    pid: int | None
    loginfo: JobLogInfo
    is_active: bool  # Remove this field and always derive from state dynamically?
    duration: float = 0.0
    title: str = "Background job"
    stoppable: bool = True
    deletable: bool = True
    user: str | None = None
    estimated_duration: float | None = None
    ppid: int | None = None
    logfile_path: str = ""  # Move out of job status -> Has a static value
    acknowledged_by: str | None = None
    lock_wato: bool = False
    # Only used by ServiceDiscoveryBackgroundJob
    host_name: str = ""


@dataclass
class BackgroundStatusSnapshot:
    job_id: JobId
    status: JobStatusSpec
    exists: bool
    is_active: bool
    has_exception: bool
    acknowledged_by: str | None
    may_stop: bool
    may_delete: bool

    def to_dict(self) -> dict:
        job_snapshot = asdict(self)
        if "status" in job_snapshot:
            # additional conversion due to pydantic usage for status only
            status: BaseModel = job_snapshot["status"]
            job_snapshot["status"] = status.model_dump()
        return job_snapshot

    @classmethod
    def from_dict(cls, data: dict) -> "BackgroundStatusSnapshot":
        data["status"] = JobStatusSpec(**data["status"])
        return cls(**data)
