#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import asyncio
import io
import re
import sys
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from typing import Callable, Coroutine, Final, Iterator, Protocol, Sequence

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from cmk.utils import paths

from cmk.base import config
from cmk.base.automations import AutomationExitCode

from ._log import logger

APPLICATION_MAX_REQUEST_TIMEOUT: Final = 60


class AutomationRequest(BaseModel, frozen=True):
    name: str
    args: Sequence[str]
    stdin: str
    log_level: int


class AutomationResponse(BaseModel, frozen=True):
    exit_code: int
    output: str


def reload_automation_config() -> None:
    config.load_all_plugins(local_checks_dir=paths.local_checks_dir, checks_dir=paths.checks_dir)
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
    # TODO: remove `reload_config` when automation helper is fully integrated.
    def execute(self, cmd: str, args: list[str], *, reload_config: bool) -> AutomationExitCode: ...


def get_application(*, engine: AutomationEngine, reload_config: Callable[[], None]) -> FastAPI:
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def timeout_middleware(
        request: Request, call_next: Callable[[Request], Coroutine[None, None, Response]]
    ) -> Response:
        if timeout_header := re.match(r"timeout=(\d+)", request.headers.get("keep-alive", "")):
            timeout = min(int(timeout_header.group(1)), APPLICATION_MAX_REQUEST_TIMEOUT)
        else:
            timeout = APPLICATION_MAX_REQUEST_TIMEOUT
        try:
            return await asyncio.wait_for(call_next(request), timeout=float(timeout))
        except asyncio.TimeoutError:
            resp = AutomationResponse(
                exit_code=AutomationExitCode.TIMEOUT,
                output=f"Timed out after {timeout} seconds",
            )
            return JSONResponse(resp.model_dump(), status_code=status.HTTP_408_REQUEST_TIMEOUT)

    @app.post("/automation")
    async def automation(request: AutomationRequest) -> AutomationResponse:
        # TODO: move this into the application lifespan once the watcher is integrated.
        reload_config()

        logger.setLevel(request.log_level)

        with (
            redirect_stdout(output_buffer := io.StringIO()),
            redirect_stderr(output_buffer),
            redirect_stdin(io.StringIO(request.stdin)),
        ):
            try:
                # TODO: remove `reload_config` when automation helper is fully integrated.
                exit_code = engine.execute(request.name, list(request.args), reload_config=False)
            except SystemExit:
                exit_code = AutomationExitCode.SYSTEM_EXIT

            return AutomationResponse(exit_code=exit_code, output=output_buffer.getvalue())

    @app.get("/health")
    async def check_health():
        return {"up": True}

    return app
