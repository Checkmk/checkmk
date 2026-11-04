#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ruff: noqa: SLF001
"""Unit tests for :mod:`tests.testlib.pytest_helpers.timeouts`.

timeout_detected logic, _default_timeout_handler branching, and _is_pytest_alive()
are exercised here. The tests that let the timeout fire signal the test process
itself, or a forked child where the process must exit.
"""

import contextlib
import multiprocessing
import signal
import subprocess
import time
from unittest.mock import MagicMock, patch

import pytest
from psutil import Process, STATUS_ZOMBIE

from tests.testlib.pytest_helpers.timeouts import MonitorTimeout, SessionTimeoutError


def test_timeout_not_detected_within_deadline() -> None:
    monitor = MonitorTimeout(timeout=100)
    assert not monitor.timeout_detected


def test_timeout_detected_after_deadline() -> None:
    monitor = MonitorTimeout(timeout=1)
    monitor._start_time -= 2
    assert monitor.timeout_detected


def test_default_timeout_handler_raises_session_timeout_error_when_timed_out() -> None:
    monitor = MonitorTimeout(timeout=1)
    monitor._start_time -= 2
    with pytest.raises(SessionTimeoutError):
        monitor._default_timeout_handler(signal.SIGINT, None)


def test_default_timeout_handler_raises_keyboard_interrupt_when_not_timed_out() -> None:
    monitor = MonitorTimeout(timeout=100)
    with pytest.raises(KeyboardInterrupt):
        monitor._default_timeout_handler(signal.SIGINT, None)


def test_is_pytest_alive_returns_true_for_current_process() -> None:
    # _pytest_pid is set to os.getpid() in __init__, which is the running test process.
    monitor = MonitorTimeout(timeout=100)
    assert monitor._is_pytest_alive()


def test_is_pytest_alive_returns_false_for_nonexistent_pid() -> None:
    monitor = MonitorTimeout(timeout=100)
    monitor._pytest_pid = 999_999_999  # above Linux PID_MAX; guaranteed to not exist
    assert not monitor._is_pytest_alive()


def test_is_pytest_alive_returns_false_for_zombie_process() -> None:
    monitor = MonitorTimeout(timeout=100)
    mock_proc = MagicMock()
    mock_proc.status.return_value = STATUS_ZOMBIE
    with patch("tests.testlib.pytest_helpers.timeouts.Process", return_value=mock_proc):
        assert not monitor._is_pytest_alive()


def _ends_within(process: subprocess.Popen[bytes], seconds: float) -> bool:
    try:
        process.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        return False
    return True


def test_timeout_interrupts_a_running_child_process() -> None:
    # No check of the exit status: where SIGCHLD is ignored (as in CI), the kernel
    # reaps the child and Popen reports 0 instead of -SIGINT.
    with pytest.raises(SessionTimeoutError), MonitorTimeout(timeout=1):
        child = subprocess.Popen(["sleep", "60"])
        child.wait()
        time.sleep(60)

    assert _ends_within(child, seconds=5)


def test_no_monitor_process_outlives_the_block() -> None:
    children_before = Process().children()

    with MonitorTimeout(timeout=100):
        pass

    assert Process().children() == children_before


def _timed_out_run_with_wedged_shutdown() -> None:
    with contextlib.suppress(SessionTimeoutError), MonitorTimeout(timeout=1, exit_after_grace=1):
        time.sleep(60)
    time.sleep(60)


def _run_with_wedged_shutdown() -> int | None:
    run = multiprocessing.get_context("fork").Process(target=_timed_out_run_with_wedged_shutdown)
    run.start()
    run.join(timeout=30)
    run.kill()
    return run.exitcode


def test_wedged_shutdown_after_the_timeout_is_ended_by_force() -> None:
    exitcode = _run_with_wedged_shutdown()

    assert exitcode == pytest.ExitCode.INTERRUPTED


def test_forced_exit_dumps_the_stack_of_the_wedged_code(capfd: pytest.CaptureFixture[str]) -> None:
    _run_with_wedged_shutdown()

    assert "_timed_out_run_with_wedged_shutdown" in capfd.readouterr().err
