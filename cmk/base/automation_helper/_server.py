#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import gunicorn.app.base  # type: ignore[import-untyped]
from fastapi import FastAPI

from ._config import ServerConfig


def run(
    config: ServerConfig,
    app: FastAPI,
) -> None:
    _ApplicationServer(app, config).run()


class _ApplicationServer(gunicorn.app.base.BaseApplication):  # type: ignore[misc] # pylint: disable=abstract-method
    def __init__(
        self,
        app: FastAPI,
        config: ServerConfig,
    ) -> None:
        self._app = app
        self._config = config
        super().__init__()

    def load_config(self) -> None:
        self.cfg.set("proc_name", "automation-helper")
        self.cfg.set("umask", 0o077)
        self.cfg.set("bind", f"unix:{self._config.unix_socket}")
        self.cfg.set("workers", self._config.num_workers)
        self.cfg.set("worker_class", "uvicorn_worker.UvicornWorker")
        self.cfg.set("pidfile", str(self._config.pid_file))
        self.cfg.set("accesslog", str(self._config.access_log))
        self.cfg.set("errorlog", str(self._config.error_log))
        # clients can dynamically set a timeout per request
        self.cfg.set("timeout", 0)

    def load(self) -> FastAPI:
        return self._app
