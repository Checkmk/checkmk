#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import logging
import os
import socketserver
import subprocess
import sys
from collections.abc import Iterator
from multiprocessing import Process
from pathlib import Path

logger = logging.getLogger(__name__)

agent_controller_path = Path(os.getenv("CMK_AGENT_CTL", "/usr/bin/cmk-agent-ctl"))


class _CMKAgentSocketHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        self.request.sendall(
            subprocess.run(
                ["check_mk_agent"],
                input=self.request.recv(1024),
                capture_output=True,
                close_fds=True,
                check=True,
            ).stdout
        )


def _clear_controller_connections(ctl_path: Path) -> None:
    subprocess.run([ctl_path.as_posix(), "delete-all"], check=False)


@contextlib.contextmanager
def _provide_agent_unix_socket() -> Iterator[None]:
    socket_address = Path("/run/check-mk-agent.socket")
    socket_address.unlink(missing_ok=True)
    proc = Process(
        target=socketserver.UnixStreamServer(
            server_address=str(socket_address),
            RequestHandlerClass=_CMKAgentSocketHandler,
        ).serve_forever
    )
    proc.start()
    socket_address.chmod(0o777)
    try:
        yield
    finally:
        proc.kill()
        socket_address.unlink(missing_ok=True)


def _run_controller_daemon(ctl_path: Path) -> int:
    with subprocess.Popen(
        [ctl_path.as_posix(), "daemon"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        close_fds=True,
        encoding="utf-8",
    ) as proc:
        exit_code = proc.wait()
        stdout, stderr = proc.communicate()
        logger.info("Stdout from controller daemon process:\n%s", stdout)
        logger.info("Stderr from controller daemon process:\n%s", stderr)

    return exit_code


@contextlib.contextmanager
def _clean_agent_controller(ctl_path: Path) -> Iterator[None]:
    _clear_controller_connections(ctl_path)
    try:
        yield
    finally:
        _clear_controller_connections(ctl_path)


@contextlib.contextmanager
def agent_controller_daemon(ctl_path: Path) -> Iterator[int]:
    """Manually take over systemds job if we are in a container (where we have no systemd)."""
    with _clean_agent_controller(ctl_path), _provide_agent_unix_socket():
        yield _run_controller_daemon(ctl_path)


if __name__ == "__main__":
    with agent_controller_daemon(agent_controller_path) as rc:
        sys.exit(rc)
