#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from contextlib import contextmanager
from logging import Logger
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel


class ServerConfig(BaseModel, frozen=True):
    unix_socket: Path
    access_log: Path
    error_log: Path


def default_config(omd_root: Path, run_path: Path, log_path: Path) -> ServerConfig:
    return ServerConfig(
        unix_socket=run_path / "ui-job-scheduler.sock",
        access_log=log_path / "access.log",
        error_log=log_path / "error.log",
    )


def run_server(config: ServerConfig, app: FastAPI, logger: Logger) -> None:
    logger.info("Starting server")
    try:
        with fix_uvicorn_unix_socket_permissions(config.unix_socket):
            uvicorn.run(
                app,
                uds=str(config.unix_socket),
                log_config={
                    "version": 1,
                    "disable_existing_loggers": False,
                    "formatters": {
                        "default": {
                            "()": "uvicorn.logging.DefaultFormatter",
                            "fmt": "%(asctime)s [%(levelno)s] [%(process)d/%(threadName)s] %(message)s",
                            "use_colors": None,
                        },
                        "access": {
                            "()": "uvicorn.logging.AccessFormatter",
                            "fmt": "%(asctime)s %(message)s",
                        },
                    },
                    "handlers": {
                        "default": {
                            "class": "logging.FileHandler",
                            "filename": str(config.error_log),
                            "formatter": "default",
                        },
                        "access": {
                            "class": "logging.FileHandler",
                            "filename": str(config.access_log),
                            "formatter": "access",
                        },
                    },
                    "loggers": {
                        "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
                        "uvicorn.error": {"level": "INFO"},
                        "uvicorn.access": {
                            "handlers": ["access"],
                            "level": "INFO",
                            "propagate": False,
                        },
                    },
                },
            )
    finally:
        logger.info("Stopped server")


@contextmanager
def fix_uvicorn_unix_socket_permissions(unix_socket: Path) -> Iterator[None]:
    """Correct unix socket permissions

    Uvicorn hard codes permissions of the unix socket to 0o600 on creation, without providing a way
    to configure this. We try to change this as soon as possible after creation of the socket.

    Unfortunately this is a bit of a hack which may influence other instances of uvicorn running if
    called from the same process. Better would be to have the permissions configurable in uvicorn
    itself. If this turns out to be a bad approach, consider doing so.
    """
    orig_main_loop = uvicorn.server.Server.main_loop

    try:

        async def new_main_loop(self: uvicorn.server.Server) -> None:
            unix_socket.chmod(0o600)
            await orig_main_loop(self)

        uvicorn.server.Server.main_loop = new_main_loop  # type: ignore[method-assign]
        yield
    finally:
        uvicorn.server.Server.main_loop = orig_main_loop  #  type: ignore[method-assign]
