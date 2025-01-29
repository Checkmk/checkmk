#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import sys
import time
from collections.abc import AsyncGenerator, Callable, Iterator, Sequence
from contextlib import asynccontextmanager, contextmanager, redirect_stderr, redirect_stdout
from logging import Formatter, getLogger
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
    error: str


class HealthCheckResponse(BaseModel, frozen=True):
    last_reload_at: float


def reload_automation_config() -> None:
    cache_manager.clear()
    config.load(validate_hosts=False)


def clear_caches_before_each_call() -> None:
    config.get_config_cache().ruleset_matcher.clear_caches()


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
    clear_caches_before_each_call: Callable[[], None],
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
        # Setting the access log format via config did not work as intended with uvicorn. This
        # seems to be a known issue: https://github.com/encode/uvicorn/issues/527
        for handler in getLogger("uvicorn.access").handlers:
            handler.setFormatter(Formatter("%(asctime)s %(message)s"))

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

        buffer_stdout = io.StringIO()
        buffer_stderr = io.StringIO()
        with (
            TRACER.span(
                f"automation[{payload.name}]",
                attributes={
                    "cmk.automation.name": payload.name,
                    "cmk.automation.args": payload.args,
                },
            ),
            redirect_stdout(buffer_stdout),
            redirect_stderr(buffer_stderr),
            redirect_stdin(io.StringIO(payload.stdin)),
            temporary_log_level(LOGGER, payload.log_level),
        ):
            clear_caches_before_each_call()
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

            return AutomationResponse(
                exit_code=exit_code,
                output=buffer_stdout.getvalue(),
                error=buffer_stderr.getvalue(),
            )

    @app.get("/health")
    async def check_health(request: Request) -> HealthCheckResponse:
        return HealthCheckResponse(last_reload_at=request.app.state.last_reload_at)

    return app
