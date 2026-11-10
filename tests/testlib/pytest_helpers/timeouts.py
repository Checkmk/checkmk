#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Terminate a test session cleanly after a given duration.

This module provides a context manager to monitor the duration of code execution
and handle correct termination of all processes if a specified timeout is exceeded.

It is also a pytest plugin: registered from a conftest's `pytest_addoption` (see
`tests.testlib.pytest_helpers.register`), it adds `--session-timeout`, wraps the
session in the monitor and stops the run cleanly when the timeout hits.
"""

import faulthandler
import multiprocessing
import os
import signal
import threading
import time
from collections.abc import Callable, Iterator
from types import FrameType, TracebackType
from typing import override, Self

import pytest
from psutil import NoSuchProcess, Process, STATUS_ZOMBIE

from tests.testlib.common.utils2 import is_containerized, run
from tests.testlib.pytest_helpers.diagnostics import add_process_snapshot


class SessionTimeoutError(BaseException): ...


_MONITOR_JOIN_TIMEOUT = 5.0


class MonitorTimeout:
    def __init__(
        self,
        timeout: int,
        timeout_handler: Callable[[int, FrameType | None], None] | None = None,
        exit_after_grace: int | None = None,
        dump_fd: int = 2,
    ):
        """Contextmanager to monitor duration of a code snippet.

        A `SessionTimeoutError` is triggered by the contextmanager after `timeout` seconds.

        Example workflow is as follows
        ```
        pytest-run -> test-A -> test-B: terminated by M1 - SessionTimeoutError -> exit
           \\                       \\-> child process - terminated by M1 -/
            \\-> monitor - M1 -> timeout! -/
        ```

        If `exit_after_grace` is set and the process is still alive `exit_after_grace`
        seconds after the timeout, it dumps the stacks of all threads to `dump_fd` and
        exits hard with pytest's "interrupted" exit code. This bounds a shutdown that
        wedges after the timeout, including the joins of threads and child processes at
        interpreter exit.

        NOTE: `timeout` of `<= 0` disables timeout monitoring.
        """
        # defaults
        self._start_time = time.monotonic()
        self._timeout_handler = timeout_handler or self._default_timeout_handler
        self._pytest_pid = os.getpid()
        # interface
        self._timeout = timeout
        self._exit_after_grace = exit_after_grace
        self._dump_fd = dump_fd
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
        return (time.monotonic() - self._start_time) >= float(self._timeout)

    def _terminate_children_processes(self) -> None:
        """Terminate the children processes.

        Processes deepest in the process-hierarchy are terminated first.
        """
        try:
            children = Process(self._pytest_pid).children(recursive=True)
        except NoSuchProcess:
            return
        children.reverse()
        for child in children:
            if child.pid != self._process.pid:
                _interrupt(child.pid)

    def _stop_monitor(self) -> None:
        """Stop and reap the monitor, so that interpreter exit has no child to wait for."""
        self._process.kill()
        self._process.join(_MONITOR_JOIN_TIMEOUT)

    def __enter__(self) -> Self:
        if self._timeout > 0:
            signal.signal(signal.SIGINT, self._timeout_handler)
            self._process.start()
            if self._exit_after_grace is not None:
                # A thread rather than faulthandler.dump_traceback_later(): pytest cancels
                # that timer whenever a test fails.
                threading.Thread(
                    target=_exit_after,
                    args=(self._timeout + self._exit_after_grace, self._dump_fd),
                    name="session-timeout-watchdog",
                    daemon=True,
                ).start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._timeout <= 0:
            return
        try:
            # A timeout signal arriving now must not abort the cleanup below.
            signal.signal(signal.SIGINT, signal.SIG_IGN)
        finally:
            self._stop_monitor()
            signal.signal(signal.SIGINT, self._sigint_handler)


def _interrupt(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGINT)
    except ProcessLookupError:
        pass
    except PermissionError:
        # Child processes (e.g. site commands) may run as root.
        run(["kill", f"-{signal.SIGINT}", str(pid)], sudo=True, check=False)


def _exit_after(seconds: float, dump_fd: int) -> None:
    time.sleep(seconds)
    try:
        os.write(
            dump_fd, b"\nThe run outlived its session timeout and grace period; forcing exit.\n"
        )
        faulthandler.dump_traceback(file=dump_fd, all_threads=True)
    finally:
        os._exit(pytest.ExitCode.INTERRUPTED)


class FunctionTimeout(MonitorTimeout):
    """Like MonitorTimeout, but raises a plain TimeoutError instead of SessionTimeoutError.

    This module's pytest_exception_interact() sets `session.shouldstop` on
    SessionTimeoutError, aborting the whole run - appropriate for the suite-wide
    --session-timeout use, but not for bounding a single call inside one test. A plain
    TimeoutError only adds diagnostics there and lets the suite continue with the next test.
    """

    @override
    def _default_timeout_handler(self, signum: int, frame: FrameType | None) -> None:
        if self.timeout_detected:
            raise TimeoutError(f"Run duration exceeds {self._timeout} seconds!")
        raise KeyboardInterrupt


SESSION_TIMEOUT_OPTION = "--session-timeout"
# Time the run gets after the session timeout to tear down and exit before it is killed.
SESSION_SHUTDOWN_GRACE = 900
_STDERR_FD = pytest.StashKey[int]()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        SESSION_TIMEOUT_OPTION,
        action="store",
        metavar="TIMEOUT",
        default=0,
        type=int,
        help="Terminate testsuite run cleanly after TIMEOUT seconds. By default, 0 (disabled).",
    )


def pytest_configure(config: pytest.Config) -> None:
    # Capture is suspended here, so fd 2 is the real stderr; later, during a test, it is
    # pytest's capture file. Never closed: a forced exit may need it until the very end.
    config.stash[_STDERR_FD] = os.dup(2)


@pytest.fixture(scope="session", autouse=True)  # ruff: ignore[pytest-fixture-autouse]
def _session_timeout(pytestconfig: pytest.Config) -> Iterator[None]:
    with MonitorTimeout(
        timeout=pytestconfig.getoption(SESSION_TIMEOUT_OPTION),
        exit_after_grace=SESSION_SHUTDOWN_GRACE,
        dump_fd=pytestconfig.stash[_STDERR_FD],
    ):
        yield


@pytest.hookimpl(tryfirst=True)
def pytest_exception_interact(
    node: pytest.Item | pytest.Collector,
    call: pytest.CallInfo[object],
    report: pytest.CollectReport | pytest.TestReport,
) -> None:
    if not (excinfo := call.excinfo):
        return
    if excinfo.type is SessionTimeoutError:
        # Prevents execution of the next test and exits the pytest-run, and
        # leads to clean termination of the affected test run.
        node.session.shouldstop = True
    elif excinfo.type is TimeoutError:
        add_process_snapshot(excinfo.value, sudo=is_containerized())
        report.longrepr = node.repr_failure(excinfo)
