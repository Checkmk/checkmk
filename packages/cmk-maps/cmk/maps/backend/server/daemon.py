#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The Maps daemon: forks into the background and serves until it gets SIGTERM.

Started by ``cmk-maps-server start`` as ``python -m cmk.maps.backend.server.daemon``.
"""

import logging
import logging.config
import os
import signal
import socket
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import FrameType
from typing import NoReturn

import uvicorn

from cmk.ccc.daemon import daemonize, pid_file_lock
from cmk.ccc.log import CMKFormatter
from cmk.maps.backend.server.main import MapsServer
from cmk.maps.backend.server.protocol import StreamClosingProtocol

_APPLICATION = "cmk.maps.backend.main:app"
_SHUTDOWN_TIMEOUT = 30
_BACKLOG = 2048
_SOCKET_PERMISSIONS = 0o660

logger = logging.getLogger(__name__)


@contextmanager
def _listening_socket(path: Path) -> Iterator[int]:
    # Bound here rather than by uvicorn, which creates the socket world-writable.
    # Listening right away queues the clients that arrive while the app starts up.
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            path.unlink(missing_ok=True)
            sock.bind(str(path))
            path.chmod(_SOCKET_PERMISSIONS)
            sock.listen(_BACKLOG)
            yield sock.fileno()
    finally:
        path.unlink(missing_ok=True)


def _exit_on_sigterm(_signum: int, _frame: FrameType | None) -> NoReturn:
    sys.exit(0)


def _log_config(log_dir: Path) -> dict[str, object]:
    # WatchedFileHandler reopens a file that logrotate has moved away.
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {"()": CMKFormatter, "with_process": True},
            "access": {"()": CMKFormatter},
        },
        "handlers": {
            "error_file": {
                "class": "logging.handlers.WatchedFileHandler",
                "filename": str(log_dir / "error.log"),
                "formatter": "default",
                "encoding": "utf-8",
            },
            "access_file": {
                "class": "logging.handlers.WatchedFileHandler",
                "filename": str(log_dir / "access.log"),
                "formatter": "access",
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "uvicorn.access": {
                "handlers": ["access_file"],
                "level": "INFO",
                "propagate": False,
            },
        },
        "root": {"level": "INFO", "handlers": ["error_file"]},
    }


def main() -> None:
    server = MapsServer(Path(os.environ["OMD_ROOT"]))
    server.log_dir.mkdir(parents=True, exist_ok=True)
    daemonize()
    # Configured before anything can fail: the daemon has no stderr any more.
    logging.config.dictConfig(_log_config(server.log_dir))
    try:
        with pid_file_lock(server.pid_file), _listening_socket(server.socket) as fd:
            # uvicorn re-raises the SIGTERM it stopped on: end with exit code 0 and
            # let the context managers clean up instead of dying from the signal.
            signal.signal(signal.SIGTERM, _exit_on_sigterm)
            uvicorn.run(
                _APPLICATION,
                fd=fd,
                backlog=_BACKLOG,
                # h11 is what "auto" picks anyway: httptools is not shipped.
                http=StreamClosingProtocol,
                timeout_graceful_shutdown=_SHUTDOWN_TIMEOUT,
                log_config=None,
            )
    except Exception:
        logger.exception("The Maps daemon stopped with an error")
        raise


if __name__ == "__main__":
    main()
