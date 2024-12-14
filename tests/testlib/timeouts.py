#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import multiprocessing
import os
import signal
import time
from types import FrameType, TracebackType
from typing import Callable, Self

from psutil import Process

from tests.testlib.utils import run


class SessionTimeoutError(TimeoutError): ...


class MonitorTimeout:
    def __init__(
        self,
        timeout: int,
        timeout_handler: Callable | None = None,
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
        self._group_pid = os.getpgrp()
        # interface
        self._timeout = timeout
        self._process = multiprocessing.Process(target=self._timeout_and_interrupt, args=())
        self._sigint_handler = signal.getsignal(signal.SIGINT)

    def _default_timeout_handler(self, signum: int, frame: FrameType | None) -> None:
        """Handle SIGINT / KeyboardInterrupt as TimeoutError / SessionTimeoutError.

        Handling of SIGINT as SessionTimeoutError is active ONLY within pytest run.
        """
        if self.timeout_detected:
            raise SessionTimeoutError(f"Run duration exceeds {self._timeout} seconds!")
        # default behaviour
        raise KeyboardInterrupt()

    def _timeout_and_interrupt(self) -> None:
        """Interrupt pytest run with `SIGINT` when a timeout is detected.

        This method is executed in a process which runs concurrently to the pytest run.
        """
        time.sleep(self._timeout)

        self._terminate_children_processes()
        # send SIGINT to pytest run.
        run(["kill", f"-{signal.SIGINT}", str(self._group_pid)], sudo=True, check=False)

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
        children = Process(self._group_pid).children(recursive=True)
        children.reverse()
        for child in children:
            if child.pid != self._process.pid:
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
