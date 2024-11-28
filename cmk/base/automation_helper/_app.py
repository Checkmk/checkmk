#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import sys
import time
from collections.abc import AsyncGenerator, Callable, Iterator, Sequence
from contextlib import asynccontextmanager, contextmanager, redirect_stderr, redirect_stdout
from typing import Protocol

from fastapi import FastAPI, Request
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel

from cmk.utils import paths
from cmk.utils.caching import cache_manager

from cmk.base import config
from cmk.base.automations import AutomationExitCode

from ._cache import Cache
from ._log import LOGGER, temporary_log_level
from ._tracer import TRACER


class AutomationPayload(BaseModel, frozen=True):
    name: str
    args: Sequence[str]
    stdin: str
    log_level: int


class AutomationResponse(BaseModel, frozen=True):
    exit_code: int
    output: str


class HealthCheckResponse(BaseModel, frozen=True):
    last_reload_at: float


def reload_automation_config() -> None:
    cache_manager.clear()
    config.load(validate_hosts=False)


@contextmanager
def redirect_stdin(stream: io.StringIO) -> Iterator[None]:
    orig_stdin = sys.stdin
    try:
        sys.stdin = stream
        yield
    finally:
        sys.stdin = orig_stdin


class AutomationEngine(Protocol):
    def execute(
        self,
        cmd: str,
        args: list[str],
        *,
        called_from_automation_helper: bool,
    ) -> AutomationExitCode: ...


def get_application(
    *,
    engine: AutomationEngine,
    cache: Cache,
    reload_config: Callable[[], None],
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
        app.state.last_reload_at = time.time()
        config.load_all_plugins(
            local_checks_dir=paths.local_checks_dir, checks_dir=paths.checks_dir
        )
        reload_config()
        yield

    app = FastAPI(lifespan=lifespan, openapi_url=None, docs_url=None, redoc_url=None)

    FastAPIInstrumentor.instrument_app(app)

    @app.post("/automation")
    async def automation(request: Request, payload: AutomationPayload) -> AutomationResponse:
        LOGGER.info("[automation] %s with args: %s received.", payload.name, payload.args)
        if cache.reload_required(request.app.state.last_reload_at):
            request.app.state.last_reload_at = time.time()
            reload_config()
            LOGGER.warning("[automation] configurations were reloaded due to a stale state.")

        with (
            TRACER.span(
                f"automation[{payload.name}]",
                attributes={
                    "cmk.automation.name": payload.name,
                    "cmk.automation.args": payload.args,
                },
            ),
            redirect_stdout(output_buffer := io.StringIO()),
            redirect_stderr(output_buffer),
            redirect_stdin(io.StringIO(payload.stdin)),
            temporary_log_level(LOGGER, payload.log_level),
        ):
            try:
                exit_code: int = engine.execute(
                    payload.name,
                    list(payload.args),
                    called_from_automation_helper=True,
                )
            except SystemExit as system_exit:
                LOGGER.error("[automation] command raised a system exit exception.")
                exit_code = (
                    system_exit_code
                    if isinstance(system_exit_code := system_exit.code, int)
                    else AutomationExitCode.UNKNOWN_ERROR
                )
            else:
                LOGGER.info("[automation] %s with args: %s processed.", payload.name, payload.args)

            return AutomationResponse(exit_code=exit_code, output=output_buffer.getvalue())

    @app.get("/health")
    async def check_health(request: Request) -> HealthCheckResponse:
        return HealthCheckResponse(last_reload_at=request.app.state.last_reload_at)

    return app
