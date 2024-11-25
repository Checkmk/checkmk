#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Launches automation helper application for processing automation commands."""

import asyncio
import dataclasses
import io
import logging
import os
import re
import sys
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Callable, Coroutine, Final, Iterator, Protocol, Sequence

import gunicorn.app.base  # type: ignore[import-untyped]
import gunicorn.util  # type: ignore[import-untyped]
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from setproctitle import setproctitle

from cmk.utils import paths

from . import config
from .automations import AutomationExitCode, automations

APPLICATION_PROCESS_TITLE: Final = "cmk-automation-helper"
APPLICATION_LOG_DIRECTORY: Final = "automation-helper"
APPLICATION_LOGGER: Final = "automation-helper"
APPLICATION_ACCESS_LOG: Final = "access.log"
APPLICATION_ERROR_LOG: Final = "error.log"
APPLICATION_MAX_REQUEST_TIMEOUT: Final = 60
APPLICATION_PID_FILE: Final = "automation-helper.pid"
APPLICATION_SOCKET: Final = "unix:tmp/run/automation-helper.sock"
APPLICATION_WORKER_CLASS: Final = "uvicorn.workers.UvicornWorker"
APPLICATION_WORKER_COUNT: Final = 2


logger = logging.getLogger(APPLICATION_LOGGER)


def configure_logger(log_directory: Path) -> None:
    handler = logging.FileHandler(log_directory / f"{APPLICATION_LOGGER}.log", encoding="UTF-8")
    formatter = logging.Formatter("%(asctime)s [%(levelno)s] [%(name)s %(process)d] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


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
    def execute(self, cmd: str, args: list[str]) -> AutomationExitCode: ...


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
                exit_code = engine.execute(request.name, list(request.args))
            except SystemExit:
                exit_code = AutomationExitCode.SYSTEM_EXIT

            return AutomationResponse(exit_code=exit_code, output=output_buffer.getvalue())

    @app.get("/health")
    async def check_health():
        return {"up": True}

    return app


@dataclasses.dataclass(frozen=True)
class ApplicationServerConfig:
    daemon: bool
    pid_file: Path
    access_log: Path
    error_log: Path


class ApplicationServer(gunicorn.app.base.BaseApplication):  # type: ignore[misc] # pylint: disable=abstract-method
    def __init__(self, app: FastAPI, cfg: ApplicationServerConfig) -> None:
        self._app = app
        self._options = {
            "daemon": cfg.daemon,
            "umask": 0o077,
            "bind": APPLICATION_SOCKET,
            "workers": APPLICATION_WORKER_COUNT,
            "worker_class": APPLICATION_WORKER_CLASS,
            "pidfile": str(cfg.pid_file),
            "accesslog": str(cfg.access_log),
            "errorlog": str(cfg.error_log),
        }
        super().__init__()

    def load_config(self) -> None:
        assert self.cfg is not None, "Default server config expected to be loaded post-init."
        for key, value in self._options.items():
            self.cfg.set(key, value)

    def load(self) -> FastAPI:
        return self._app

    def run(self) -> None:
        assert self.cfg is not None, "Gunicorn server config is required to run application."
        if self.cfg.daemon:
            gunicorn.util.daemonize()
        super().run()


def main() -> int:
    try:
        setproctitle(APPLICATION_PROCESS_TITLE)
        os.unsetenv("LANG")

        omd_root = Path(os.environ.get("OMD_ROOT", ""))
        run_directory = omd_root / "tmp" / "run"
        log_directory = omd_root / "var" / "log" / APPLICATION_LOG_DIRECTORY

        run_directory.mkdir(exist_ok=True, parents=True)
        log_directory.mkdir(exist_ok=True, parents=True)

        configure_logger(log_directory)

        app = get_application(engine=automations, reload_config=reload_automation_config)

        server_config = ApplicationServerConfig(
            daemon=True,
            pid_file=run_directory / APPLICATION_PID_FILE,
            access_log=log_directory / APPLICATION_ACCESS_LOG,
            error_log=log_directory / APPLICATION_ERROR_LOG,
        )

        ApplicationServer(app, server_config).run()

    except Exception:
        return 1

    return 0
