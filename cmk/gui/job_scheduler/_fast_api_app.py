#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import os
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager
from logging import Logger
from pathlib import Path
from typing import get_type_hints, override

from fastapi import FastAPI, Request
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from starlette.responses import Response

from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundJobsHealth,
    HealthResponse,
    IsAliveRequest,
    IsAliveResponse,
    JobExecutor,
    JobTarget,
    ProcessHealth,
    ScheduledJobsHealth,
    StartRequest,
    StartResponse,
    TerminateRequest,
)

from ._scheduler import filter_running_jobs, SchedulerState
from ._scheduler import reset_scheduling as reset_job_scheduling


def get_application(
    logger: Logger,
    loaded_at: int,
    registered_jobs: Mapping[str, type[BackgroundJob]],
    executor: JobExecutor,
    process_health: Callable[[], ProcessHealth],
    scheduler_state: SchedulerState,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        # The code before `yield` is executed on startup, after `yield` on shutdown
        logger.info("Starting background jobs on_scheduler_start hooks")
        for job_cls in registered_jobs.values():
            job_cls.on_scheduler_start(executor, debug=False)
        logger.info("Finished on_scheduler_start hooks")
        yield

    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None, lifespan=lifespan)
    app.state.loaded_at = loaded_at

    FastAPIInstrumentor.instrument_app(app)

    @app.post("/start")
    async def start(request: Request, payload: StartRequest) -> StartResponse:
        if not (
            result := executor.start(
                payload.type_id,
                payload.job_id,
                payload.work_dir,
                payload.span_id,
                # The generic endpoint can not know and parse the job specific args. Therefore, we need
                # to dynamically get the expected model and parse the args.
                JobTarget(
                    callable=payload.target.callable,
                    args=get_type_hints(payload.target.callable)["args"].model_validate(
                        payload.target.args
                    ),
                ),
                payload.initial_status_args,
                payload.override_job_log_level,
                payload.origin_span_context,
            )
        ).is_ok():
            return StartResponse(
                success=False,
                error_type=result.error.__class__.__name__,
                error_message=str(result.error),
            )
        return StartResponse(success=True, error_type="", error_message="")

    @app.post("/terminate")
    async def terminate(request: Request, payload: TerminateRequest) -> None:
        if (result := executor.terminate(payload.job_id)).is_error():
            raise result.error

    @app.post("/is_alive")
    async def is_alive(request: Request, payload: IsAliveRequest) -> IsAliveResponse:
        result = executor.is_alive(payload.job_id)
        if result.is_error():
            raise result.error
        return IsAliveResponse(is_alive=executor.is_alive(payload.job_id).ok)

    @app.get("/health", response_class=PrettyJSONResponse)
    async def check_health(request: Request) -> HealthResponse:
        return HealthResponse(
            loaded_at=request.app.state.loaded_at,
            process=process_health(),
            background_jobs=BackgroundJobsHealth(
                running_jobs=executor.all_running_jobs(),
                job_executions=executor.job_executions(),
            ),
            scheduled_jobs=ScheduledJobsHealth(
                next_cycle_start=scheduler_state.next_cycle_start,
                running_jobs={
                    name: job.started_at
                    for name, job in filter_running_jobs(scheduler_state.running_jobs).items()
                },
                job_executions=dict(scheduler_state.job_executions),
            ),
        )

    @app.post("/reset_scheduling")
    async def reset_scheduling(request: Request, payload: dict[str, str]) -> None:
        reset_job_scheduling(payload["job_id"])

    return app


class PrettyJSONResponse(Response):
    media_type = "application/json"

    @override
    def render(self, content: object) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=4,
            separators=(", ", ": "),
        ).encode("utf-8")


def make_process_health() -> ProcessHealth:
    # see: man proc(5).
    statm_parts = Path("/proc/self/statm").read_text().split()
    return ProcessHealth(
        pid=os.getpid(),
        ppid=os.getppid(),
        num_fds=len(list(Path("/proc/self/fd").iterdir())),
        vm_bytes=int(statm_parts[0]) * 4096,
        rss_bytes=int(statm_parts[1]) * 4096,
    )
