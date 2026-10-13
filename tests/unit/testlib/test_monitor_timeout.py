#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ruff: noqa: SLF001
"""Unit tests for :mod:`tests.testlib.pytest_helpers.timeouts`.

timeout_detected logic, _default_timeout_handler branching, and _is_pytest_alive()
are exercised here. The full timeout-fires path (os.kill to self) requires a subprocess
and is not covered at this level.
"""

import signal
from unittest.mock import MagicMock, patch

import pytest
from psutil import STATUS_ZOMBIE

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
