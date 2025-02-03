#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from cmk.base.automation_helper._app import (
    _reloader_task,
    _State,
    AutomationEngine,
    AutomationPayload,
    AutomationResponse,
    get_application,
    HealthCheckResponse,
)
from cmk.base.automation_helper._cache import Cache
from cmk.base.automation_helper._config import ReloaderConfig
from cmk.base.automations import AutomationExitCode


class _DummyAutomationEngineSuccess:
    def execute(
        self,
        cmd: str,
        args: list[str],
        *,
        called_from_automation_helper: bool,
    ) -> AutomationExitCode:
        return AutomationExitCode.SUCCESS


class _DummyAutomationEngineFailure:
    def execute(
        self,
        cmd: str,
        args: list[str],
        *,
        called_from_automation_helper: bool,
    ) -> AutomationExitCode:
        raise SystemExit(1)


_EXAMPLE_AUTOMATION_PAYLOAD = AutomationPayload(
    name="dummy", args=[], stdin="", log_level=logging.INFO
).model_dump()


def _get_test_client(
    engine: AutomationEngine,
    cache: Cache,
    reload_config: Callable[[], None],
    clear_caches_before_each_call: Callable[[], None],
) -> TestClient:
    app = get_application(
        engine=engine,
        cache=cache,
        reloader_config=ReloaderConfig(
            active=True,
            poll_interval=1.0,
            cooldown_interval=5.0,
        ),
        reload_config=reload_config,
        clear_caches_before_each_call=clear_caches_before_each_call,
    )
    return TestClient(app)


def test_automation_with_success(mocker: MockerFixture, cache: Cache) -> None:
    mock_reload_config = mocker.MagicMock()
    mock_clear_caches_before_each_call = mocker.MagicMock()
    with _get_test_client(
        _DummyAutomationEngineSuccess(),
        cache,
        mock_reload_config,
        mock_clear_caches_before_each_call,
    ) as client:
        resp = client.post("/automation", json=_EXAMPLE_AUTOMATION_PAYLOAD)

    assert resp.status_code == 200
    assert AutomationResponse.model_validate(resp.json()) == AutomationResponse(
        exit_code=AutomationExitCode.SUCCESS,
        output="",
        error="",
    )
    mock_reload_config.assert_called_once()  # only at application startup
    mock_clear_caches_before_each_call.assert_called_once()


def test_automation_with_failure(mocker: MockerFixture, cache: Cache) -> None:
    mock_reload_config = mocker.MagicMock()
    mock_clear_caches_before_each_call = mocker.MagicMock()
    with _get_test_client(
        _DummyAutomationEngineFailure(),
        cache,
        mock_reload_config,
        mock_clear_caches_before_each_call,
    ) as client:
        resp = client.post("/automation", json=_EXAMPLE_AUTOMATION_PAYLOAD)

    assert resp.status_code == 200
    assert AutomationResponse.model_validate(resp.json()) == AutomationResponse(
        exit_code=1,
        output="",
        error="",
    )
    mock_reload_config.assert_called_once()  # only at application startup
    mock_clear_caches_before_each_call.assert_called_once()


def test_automation_reloads_if_necessary(mocker: MockerFixture, cache: Cache) -> None:
    mock_reload_config = mocker.MagicMock()
    mock_clear_caches_before_each_call = mocker.MagicMock()
    with _get_test_client(
        _DummyAutomationEngineSuccess(),
        cache,
        mock_reload_config,
        mock_clear_caches_before_each_call,
    ) as client:
        last_reload_before_cache_update = HealthCheckResponse.model_validate(
            client.get("/health").json()
        ).last_reload_at
        cache.store_last_detected_change(time.time())
        client.post("/automation", json=_EXAMPLE_AUTOMATION_PAYLOAD)
        assert (
            HealthCheckResponse.model_validate(client.get("/health").json()).last_reload_at
            > last_reload_before_cache_update
        )

    assert (
        # once at application startup, once when the endpoint is called
        mock_reload_config.call_count == 2
    )
    mock_clear_caches_before_each_call.assert_called_once()


def test_health_check(cache: Cache) -> None:
    with _get_test_client(
        _DummyAutomationEngineSuccess(),
        cache,
        lambda: None,
        lambda: None,
    ) as client:
        resp = client.get("/health")

    assert resp.status_code == 200
    assert HealthCheckResponse.model_validate(resp.json()).last_reload_at < time.time()


@pytest.mark.asyncio
async def test_reloader_single_change(mocker: MockerFixture, cache: Cache) -> None:
    mock_reload_callback = mocker.MagicMock()
    state = _State(
        last_reload_at=1,
        automation_or_reload_lock=asyncio.Lock(),
    )
    mock_delay_state = _MockDelayState(
        call_counter=0,
        current_delay=0.0,
        wake_up=asyncio.Event(),
    )
    reloader_task = asyncio.create_task(
        _reloader_task(
            config=ReloaderConfig(
                active=True,
                poll_interval=0.0,
                cooldown_interval=0.0,
            ),
            cache=cache,
            reload_callback=mock_reload_callback,
            state=state,
            delayer_factory=lambda delay: _mock_delay(mock_delay_state, delay),
        )
    )

    # poll
    await _wait_for_mock_delay(mock_delay_state, 1)
    cache.store_last_detected_change(state.last_reload_at + 1)
    mock_delay_state.wake_up.set()
    # cooldown
    await _wait_for_mock_delay(mock_delay_state, 2)
    mock_delay_state.wake_up.set()
    # next poll
    await _wait_for_mock_delay(mock_delay_state, 3)

    reloader_task.cancel()
    mock_reload_callback.assert_called_once()
    assert state.last_reload_at > 1


@pytest.mark.asyncio
async def test_reloader_two_changes(mocker: MockerFixture, cache: Cache) -> None:
    mock_reload_callback = mocker.MagicMock()
    state = _State(
        last_reload_at=1,
        automation_or_reload_lock=asyncio.Lock(),
    )
    mock_delay_state = _MockDelayState(
        call_counter=0,
        current_delay=0.0,
        wake_up=asyncio.Event(),
    )
    reloader_task = asyncio.create_task(
        _reloader_task(
            config=ReloaderConfig(
                active=True,
                poll_interval=0.0,
                cooldown_interval=5.0,
            ),
            cache=cache,
            reload_callback=mock_reload_callback,
            state=state,
            delayer_factory=lambda delay: _mock_delay(mock_delay_state, delay),
        )
    )

    # poll
    await _wait_for_mock_delay(mock_delay_state, 1)
    cache.store_last_detected_change(state.last_reload_at + 1)
    mock_delay_state.wake_up.set()
    # cooldown
    await _wait_for_mock_delay(mock_delay_state, 2)
    assert mock_delay_state.current_delay == 5.0
    cache.store_last_detected_change(state.last_reload_at + 2)
    mock_delay_state.wake_up.set()
    # next cooldown
    await _wait_for_mock_delay(mock_delay_state, 3)
    mock_reload_callback.assert_not_called()
    assert mock_delay_state.current_delay == 2 - 1
    mock_delay_state.wake_up.set()
    # next poll
    await _wait_for_mock_delay(mock_delay_state, 4)

    reloader_task.cancel()
    mock_reload_callback.assert_called_once()
    assert state.last_reload_at > 1


@pytest.mark.asyncio
async def test_reloader_takes_state_into_account(mocker: MockerFixture, cache: Cache) -> None:
    mock_reload_callback = mocker.MagicMock()
    lock = _LockWithCounter()
    state = _State(
        last_reload_at=1,
        automation_or_reload_lock=lock,
    )
    mock_delay_state = _MockDelayState(
        call_counter=0,
        current_delay=0.0,
        wake_up=asyncio.Event(),
    )
    reloader_task = asyncio.create_task(
        _reloader_task(
            config=ReloaderConfig(
                active=True,
                poll_interval=0.0,
                cooldown_interval=0.0,
            ),
            cache=cache,
            reload_callback=mock_reload_callback,
            state=state,
            delayer_factory=lambda delay: _mock_delay(mock_delay_state, delay),
        )
    )

    # poll
    await _wait_for_mock_delay(mock_delay_state, 1)
    cache.store_last_detected_change(state.last_reload_at + 1)
    mock_delay_state.wake_up.set()
    # cooldown
    await _wait_for_mock_delay(mock_delay_state, 2)
    state.last_reload_at += 2
    mock_delay_state.wake_up.set()
    # next poll
    await _wait_for_mock_delay(mock_delay_state, 3)

    reloader_task.cancel()
    mock_reload_callback.assert_not_called()
    assert state.last_reload_at == 3
    assert lock.counter == 1


@dataclass
class _MockDelayState:
    call_counter: int
    current_delay: float
    wake_up: asyncio.Event


async def _mock_delay(state: _MockDelayState, delay: float) -> None:
    state.current_delay = delay
    state.call_counter += 1
    await state.wake_up.wait()
    state.wake_up.clear()


async def _wait_for_mock_delay(state: _MockDelayState, expected_call_count: int) -> None:
    while state.call_counter != expected_call_count:
        await asyncio.sleep(0.01)


class _LockWithCounter(asyncio.Lock):
    def __init__(self):
        super().__init__()
        self.counter = 0

    async def __aenter__(self) -> None:
        self.counter += 1
        return await super().__aenter__()
