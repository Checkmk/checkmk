#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module provides a context manager to monitor the duration of code execution
and handle correct termination of all processes if a specified timeout is exceeded.
"""

import multiprocessing
import os
import signal
import time
from collections.abc import Callable
from types import FrameType, TracebackType
from typing import Self

from psutil import NoSuchProcess, Process, STATUS_ZOMBIE

from tests.testlib.common.utils2 import run


class SessionTimeoutError(BaseException): ...


class MonitorTimeout:
    def __init__(
        self,
        timeout: int,
        timeout_handler: Callable[[int, FrameType | None], None] | None = None,
    ):
        """Contextmanager to monitor duration of a code snippet.

        A `SessionTimeoutError` is triggered by the contextmanager after `timeout` seconds.

        Example workflow is as follows
        ```
        pytest-run -> test-A -> test-B: terminated by M1 - SessionTimeoutError -> exit
           \\                       \\-> child process - terminated by M1 -/
            \\-> monitor - M1 -> timeout! -/
        ```

        NOTE: `timeout` of `<= 0` disables timeout monitoring.
        """
        # defaults
        self._start_time = time.time()
        self._timeout_handler = timeout_handler or self._default_timeout_handler
        self._pytest_pid = os.getpid()
        # interface
        self._timeout = timeout
        # NOTE: Things don't work out-of-the-box here for Python 3.14's default start method
        # "forkserver", see
        # https://docs.python.org/3/library/multiprocessing.html#the-spawn-and-forkserver-start-methods
        self._process = multiprocessing.get_context("fork").Process(
            target=self._timeout_and_interrupt, args=()
        )
        self._sigint_handler = signal.getsignal(signal.SIGINT)

    def _default_timeout_handler(self, signum: int, frame: FrameType | None) -> None:  # noqa: ARG002
        """Handle SIGINT as SessionTimeoutError or re-raise KeyboardInterrupt.

        Handling of SIGINT as SessionTimeoutError is active ONLY within pytest run.
        """
        if self.timeout_detected:
            raise SessionTimeoutError(f"Run duration exceeds {self._timeout} seconds!")
        # default behaviour
        raise KeyboardInterrupt

    def _is_pytest_alive(self) -> bool:
        try:
            return Process(self._pytest_pid).status() != STATUS_ZOMBIE
        except NoSuchProcess:
            return False

    def _timeout_and_interrupt(self) -> None:
        """Interrupt pytest run with `SIGINT` when a timeout is detected.

        This method is executed in a process which runs concurrently to the pytest run.
        """
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            # worst-case: the timeout-logic is invoked after 'deadline + 1' seconds.
            # considering the deadlines, this is tolerable.
            time.sleep(1.0)
            if not self._is_pytest_alive():
                return

        self._terminate_children_processes()
        # os.kill() targets a specific PID, so the monitor cannot receive its own SIGINT.
        try:
            os.kill(self._pytest_pid, signal.SIGINT)
        except ProcessLookupError:
            return  # pytest already exited; nothing to interrupt

    @property
    def timeout_detected(self) -> bool:
        return (time.time() - self._start_time) >= float(self._timeout)

    def _terminate_children_processes(self) -> None:
        """Terminate the children processes.

        Processes deepest in the process-hierarchy are terminated first.
        """
        # TODO:
        # Termination of a child process should lead to SIGCHLD being raise to parent process.
        # explore using SIGCHLD to trigger TimeoutError, instead of SIGINT.
        try:
            children = Process(self._pytest_pid).children(recursive=True)
        except NoSuchProcess:
            return
        children.reverse()
        for child in children:
            if child.pid != self._process.pid:
                # sudo is needed: child processes (e.g. site commands) may run as root.
                run(["kill", f"-{signal.SIGINT}", str(child.pid)], sudo=True, check=False)

    def __enter__(self) -> Self:
        if self._timeout > 0:
            signal.signal(signal.SIGINT, self._timeout_handler)
            self._process.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._timeout > 0:
            self._process.terminate()
            signal.signal(signal.SIGINT, self._sigint_handler)
