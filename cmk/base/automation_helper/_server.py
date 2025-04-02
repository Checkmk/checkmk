#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from uvicorn import run as run_uvicorn_server

from ._config import ServerConfig


def run(
    config: ServerConfig,
    application_factory_import_path: str,
) -> None:
    with _provide_unix_socket(
        path=config.unix_socket_path,
        permissions=config.unix_socket_permissions,
    ) as socket_file_descriptor:
        run_uvicorn_server(
            application_factory_import_path,
            factory=True,
            fd=socket_file_descriptor,
            workers=config.num_workers,
            log_config={
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "default": {
                        "()": "uvicorn.logging.DefaultFormatter",
                        "fmt": "%(asctime)s [%(levelno)s] [%(process)d] %(message)s",
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
                    "uvicorn": {
                        "handlers": ["default"],
                        "level": "INFO",
                        "propagate": False,
                    },
                    "uvicorn.error": {
                        "level": "INFO",
                    },
                    "uvicorn.access": {
                        "handlers": ["access"],
                        "level": "INFO",
                        "propagate": False,
                    },
                },
            },
        )


@contextmanager
def _provide_unix_socket(path: Path, permissions: int) -> Generator[int]:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.bind(str(path))
            path.chmod(permissions)
            yield sock.fileno()
    finally:
        path.unlink(missing_ok=True)
