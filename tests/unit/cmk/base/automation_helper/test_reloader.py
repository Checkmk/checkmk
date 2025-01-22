#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from threading import Event

from pytest_mock import MockerFixture

from tests.testlib.utils import wait_until

from cmk.base.automation_helper._cache import Cache
from cmk.base.automation_helper._config import ReloaderConfig
from cmk.base.automation_helper._reloader import run


def test_reloader_single_change(mocker: MockerFixture, cache: Cache) -> None:
    mock_reload_callback = mocker.MagicMock()
    mock_shutdown_flag = _MockEvent()
    with run(
        ReloaderConfig(
            active=True,
            poll_interval=0.0,
            cooldown_interval=0.0,
        ),
        cache,
        mock_reload_callback,
        mock_shutdown_flag,
    ):
        # poll
        _wait_until_mock_event_is_waiting(mock_shutdown_flag, 1)
        cache.store_last_detected_change(1)
        mock_shutdown_flag.stop_waiting = True
        # cooldown
        _wait_until_mock_event_is_waiting(mock_shutdown_flag, 2)
        mock_shutdown_flag.stop_waiting = True
        # ensure that we reach the next poll, otherwise, setting the flag (happens when the context
        # manager is exited) might happen too fast, preventing the reload
        _wait_until_mock_event_is_waiting(mock_shutdown_flag, 3)
    mock_reload_callback.assert_called_once()


def test_reloader_two_changes(mocker: MockerFixture, cache: Cache) -> None:
    mock_reload_callback = mocker.MagicMock()
    mock_shutdown_flag = _MockEvent()
    with run(
        ReloaderConfig(
            active=True,
            poll_interval=0.0,
            cooldown_interval=5.0,
        ),
        cache,
        mock_reload_callback,
        mock_shutdown_flag,
    ):
        # poll
        _wait_until_mock_event_is_waiting(mock_shutdown_flag, 1)
        cache.store_last_detected_change(1)
        mock_shutdown_flag.stop_waiting = True
        # cooldown
        _wait_until_mock_event_is_waiting(mock_shutdown_flag, 2)
        assert mock_shutdown_flag.current_wait_timeout == 5
        cache.store_last_detected_change(2)
        mock_shutdown_flag.stop_waiting = True
        # next cooldown
        _wait_until_mock_event_is_waiting(mock_shutdown_flag, 3)
        mock_reload_callback.assert_not_called()
        assert mock_shutdown_flag.current_wait_timeout == 2 - 1
        mock_shutdown_flag.stop_waiting = True
        # ensure that we reach the next poll, otherwise, setting the flag (happens when the context
        # manager is exited) might happen too fast, preventing the reload
        _wait_until_mock_event_is_waiting(mock_shutdown_flag, 4)
    mock_reload_callback.assert_called_once()


class _MockEvent(Event):
    def __init__(self):
        super().__init__()
        self.stop_waiting = False
        self._wait_counter = 0
        self._current_wait_timeout: float | None = None
        self._is_set = False

    def wait(self, timeout: float | None = None) -> bool:
        self._wait_counter += 1
        self._current_wait_timeout = timeout
        wait_until(
            lambda: self.stop_waiting | self._is_set,
            timeout=float("inf"),
            interval=0.01,
        )
        self.stop_waiting = False
        self._current_wait_timeout = None
        return self._is_set

    def set(self) -> None:
        self._is_set = True

    @property
    def wait_counter(self) -> int:
        return self._wait_counter

    @property
    def current_wait_timeout(self) -> float | None:
        return self._current_wait_timeout


def _wait_until_mock_event_is_waiting(
    mock_event: _MockEvent,
    expected_wait_counter: int,
) -> None:
    wait_until(
        lambda: mock_event.wait_counter == expected_wait_counter,
        timeout=float("inf"),
        interval=0.01,
    )
