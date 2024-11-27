#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Launches automation helper application for processing automation commands."""

import dataclasses
from pathlib import Path
from typing import Final

import gunicorn.app.base  # type: ignore[import-untyped]
import gunicorn.util  # type: ignore[import-untyped]
from fastapi import FastAPI

APPLICATION_SOCKET: Final = "unix:tmp/run/automation-helper.sock"
APPLICATION_WORKER_CLASS: Final = "uvicorn.workers.UvicornWorker"
APPLICATION_WORKER_COUNT: Final = 2


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
