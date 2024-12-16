#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Launches automation helper application for processing automation commands."""

import dataclasses
from collections.abc import Sequence
from pathlib import Path
from threading import Thread
from typing import Final

import gunicorn.app.base  # type: ignore[import-untyped]
from fastapi import FastAPI

from cmk.ccc.daemon import daemonize

APPLICATION_WORKER_CLASS: Final = "uvicorn.workers.UvicornWorker"
APPLICATION_WORKER_COUNT: Final = 2


@dataclasses.dataclass(frozen=True)
class ApplicationServerConfig:
    daemon: bool
    unix_socket: Path
    pid_file: Path
    access_log: Path
    error_log: Path


def run(
    app_server_config: ApplicationServerConfig,
    services: Sequence[Thread],
    app: FastAPI,
) -> None:
    if app_server_config.daemon:
        daemonize()

    for service in services:
        service.start()

    _ApplicationServer(app, app_server_config).run()


class _ApplicationServer(gunicorn.app.base.BaseApplication):  # type: ignore[misc] # pylint: disable=abstract-method
    def __init__(
        self,
        app: FastAPI,
        app_server_config: ApplicationServerConfig,
    ) -> None:
        self._app = app
        self._app_server_config = app_server_config
        super().__init__()

    def load_config(self) -> None:
        self.cfg.set("umask", 0o077)
        self.cfg.set("bind", f"unix:{self._app_server_config.unix_socket}")
        self.cfg.set("workers", APPLICATION_WORKER_COUNT)
        self.cfg.set("worker_class", APPLICATION_WORKER_CLASS)
        self.cfg.set("pidfile", str(self._app_server_config.pid_file))
        self.cfg.set("accesslog", str(self._app_server_config.access_log))
        self.cfg.set("errorlog", str(self._app_server_config.error_log))
        # clients can dynamically set a timeout per request
        self.cfg.set("timeout", 0)

    def load(self) -> FastAPI:
        return self._app
