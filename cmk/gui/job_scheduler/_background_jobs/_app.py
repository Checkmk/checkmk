#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager
from logging import Formatter, getLogger, Logger
from pathlib import Path
from typing import get_type_hints

from fastapi import FastAPI, Request
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundJobsHealth,
    HealthResponse,
    IsAliveRequest,
    IsAliveResponse,
    JobExecutor,
    JobTarget,
    ProcessHealth,
    StartRequest,
    StartResponse,
    TerminateRequest,
)


def get_application(
    logger: Logger,
    loaded_at: int,
    registered_jobs: Mapping[str, type[BackgroundJob]],
    executor: JobExecutor,
    process_health: Callable[[], ProcessHealth],
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        # Setting the access log format via config did not work as intended with uvicorn. This
        # seems to be a known issue: https://github.com/encode/uvicorn/issues/527
        for h in getLogger("uvicorn.access").handlers:
            h.setFormatter(Formatter("%(asctime)s %(message)s"))

        # The code before `yield` is executed on startup, after `yield` on shutdown
        logger.info("Starting background jobs on_scheduler_start hooks")
        for job_cls in registered_jobs.values():
            job_cls.on_scheduler_start(executor)
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
                payload.lock_wato,
                payload.is_stoppable,
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
        executor.terminate(payload.job_id)

    @app.post("/is_alive")
    async def is_alive(request: Request, payload: IsAliveRequest) -> IsAliveResponse:
        return IsAliveResponse(is_alive=executor.is_alive(payload.job_id))

    @app.get("/health")
    async def check_health(request: Request) -> HealthResponse:
        return HealthResponse(
            loaded_at=request.app.state.loaded_at,
            process=process_health(),
            background_jobs=BackgroundJobsHealth(
                running_jobs=executor.all_running_jobs(),
                job_executions=executor.job_executions(),
            ),
        )

    return app


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
