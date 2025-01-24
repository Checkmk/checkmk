#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pydantic import BaseModel

from ._interface import JobTarget, SpanContextModel


class StartRequest(BaseModel, frozen=True):
    job_id: str
    work_dir: str
    span_id: str
    # Args will be parsed specifically per job
    # (See cmk.gui.job_scheduler._background_jobs._app.get_application.start)
    target: JobTarget[dict]
    lock_wato: bool
    is_stoppable: bool
    override_job_log_level: int | None
    origin_span_context: SpanContextModel


class StartResponse(BaseModel, frozen=True):
    success: bool
    error_type: str
    error_message: str


class TerminateRequest(BaseModel, frozen=True):
    job_id: str


class IsAliveRequest(BaseModel, frozen=True):
    job_id: str


class IsAliveResponse(BaseModel, frozen=True):
    is_alive: bool


class HealthResponse(BaseModel, frozen=True):
    loaded_at: int
