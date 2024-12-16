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


class ApplicationServer(gunicorn.app.base.BaseApplication):  # type: ignore[misc] # pylint: disable=abstract-method
    def __init__(
        self, app: FastAPI, cfg: ApplicationServerConfig, *, services: Sequence[Thread]
    ) -> None:
        self._app = app
        self._services = services
        self._options = {
            "daemon": cfg.daemon,
            "umask": 0o077,
            "bind": f"unix:{cfg.unix_socket}",
            "workers": APPLICATION_WORKER_COUNT,
            "worker_class": APPLICATION_WORKER_CLASS,
            "pidfile": str(cfg.pid_file),
            "accesslog": str(cfg.access_log),
            "errorlog": str(cfg.error_log),
            # clients can dynamically set a timeout per request
            "timeout": 0,
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
            daemonize()

        for service in self._services:
            service.start()

        super().run()
