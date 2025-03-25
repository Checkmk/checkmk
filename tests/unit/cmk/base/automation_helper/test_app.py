#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import asyncio
import logging
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import override

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from tests.testlib.common.utils import wait_until

from cmk.ccc.version import Version

from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher

from cmk.automations.helper_api import AutomationPayload, AutomationResponse
from cmk.automations.results import ABCAutomationResult, SerializedResult

from cmk.base.api.agent_based.plugin_classes import AgentBasedPlugins
from cmk.base.automation_helper._app import (
    _reloader_task,
    _State,
    AutomationEngine,
    HealthCheckResponse,
    make_application,
)
from cmk.base.automation_helper._cache import Cache
from cmk.base.automation_helper._config import ReloaderConfig
from cmk.base.automations import AutomationError
from cmk.base.config import ConfigCache, LoadedConfigFragment, LoadingResult


class _DummyAutomationResult(ABCAutomationResult):
    @staticmethod
    @override
    def automation_call() -> str:
        return "dummy"

    @override
    def serialize(self, for_cmk_version: Version) -> SerializedResult:
        return SerializedResult("dummy_serialized")


class _DummyAutomationEngineSuccess:
    def execute(
        self,
        cmd: str,
        args: list[str],
        plugins: AgentBasedPlugins | None,
        loading_result: LoadingResult | None,
    ) -> _DummyAutomationResult:
        sys.stdout.write("stdout_success")
        sys.stderr.write("stderr_success")
        return _DummyAutomationResult()


class _DummyAutomationEngineFailure:
    def execute(
        self,
        cmd: str,
        args: list[str],
        plugins: AgentBasedPlugins | None,
        loading_result: LoadingResult | None,
    ) -> AutomationError:
        sys.stdout.write("stdout_failure")
        sys.stderr.write("stderr_failure")
        return AutomationError.KNOWN_ERROR


class _DummyAutomationEngineSystemExit:
    def execute(
        self,
        cmd: str,
        args: list[str],
        plugins: AgentBasedPlugins | None,
        loading_result: LoadingResult | None,
    ) -> AutomationError:
        sys.stdout.write("stdout_system_exit")
        sys.stderr.write("stderr_system_exit")
        raise SystemExit(1)


_EXAMPLE_AUTOMATION_PAYLOAD = AutomationPayload(
    name="dummy", args=[], stdin="", log_level=logging.INFO
).model_dump()


def _make_test_client(
    engine: AutomationEngine,
    cache: Cache,
    reload_config: Callable[[AgentBasedPlugins], LoadingResult],
    clear_caches_before_each_call: Callable[[RulesetMatcher], None],
    reloader_config: ReloaderConfig = ReloaderConfig(
        active=True,
        poll_interval=1.0,
        cooldown_interval=5.0,
    ),
) -> TestClient:
    return TestClient(
        make_application(
            engine=engine,
            cache=cache,
            reloader_config=reloader_config,
            reload_config=reload_config,
            clear_caches_before_each_call=clear_caches_before_each_call,
        )
    )


def test_reloader_is_running(mocker: MockerFixture, cache: Cache) -> None:
    mock_reload_config = mocker.MagicMock()
    with _make_test_client(
        _DummyAutomationEngineSuccess(),
        cache,
        mock_reload_config,
        lambda ruleset_matcher: None,
        reloader_config=ReloaderConfig(
            active=True,
            poll_interval=0.0,
            cooldown_interval=0.0,
        ),
    ) as client:
        current_last_reload_at = HealthCheckResponse.model_validate(
            client.get("/health").json()
        ).last_reload_at
        now = time.time()
        assert now > current_last_reload_at
        cache.store_last_detected_change(now)
        wait_until(
            lambda: HealthCheckResponse.model_validate(client.get("/health").json()).last_reload_at
            > current_last_reload_at,
            timeout=0.25,
            interval=0.025,
        )

    assert (
        # once at application startup, once by the reloader task
        mock_reload_config.call_count == 2
    )


def test_automation_with_success(mocker: MockerFixture, cache: Cache) -> None:
    mock_reload_config = mocker.MagicMock()
    mock_clear_caches_before_each_call = mocker.MagicMock()
    with _make_test_client(
        _DummyAutomationEngineSuccess(),
        cache,
        mock_reload_config,
        mock_clear_caches_before_each_call,
    ) as client:
        resp = client.post("/automation", json=_EXAMPLE_AUTOMATION_PAYLOAD)

    assert resp.status_code == 200
    assert AutomationResponse.model_validate(resp.json()) == AutomationResponse(
        serialized_result_or_error_code="dummy_serialized",
        stdout="stdout_success",
        stderr="stderr_success",
    )
    mock_reload_config.assert_called_once()  # only at application startup
    mock_clear_caches_before_each_call.assert_called_once()


def test_automation_with_failure(mocker: MockerFixture, cache: Cache) -> None:
    mock_reload_config = mocker.MagicMock()
    mock_clear_caches_before_each_call = mocker.MagicMock()
    with _make_test_client(
        _DummyAutomationEngineFailure(),
        cache,
        mock_reload_config,
        mock_clear_caches_before_each_call,
    ) as client:
        resp = client.post("/automation", json=_EXAMPLE_AUTOMATION_PAYLOAD)

    assert resp.status_code == 200
    assert AutomationResponse.model_validate(resp.json()) == AutomationResponse(
        serialized_result_or_error_code=1,
        stdout="stdout_failure",
        stderr="stderr_failure",
    )
    mock_reload_config.assert_called_once()  # only at application startup
    mock_clear_caches_before_each_call.assert_called_once()


def test_automation_with_system_exit(mocker: MockerFixture, cache: Cache) -> None:
    mock_reload_config = mocker.MagicMock()
    mock_clear_caches_before_each_call = mocker.MagicMock()
    with _make_test_client(
        _DummyAutomationEngineSystemExit(),
        cache,
        mock_reload_config,
        mock_clear_caches_before_each_call,
    ) as client:
        resp = client.post("/automation", json=_EXAMPLE_AUTOMATION_PAYLOAD)

    assert resp.status_code == 200
    assert AutomationResponse.model_validate(resp.json()) == AutomationResponse(
        serialized_result_or_error_code=1,
        stdout="stdout_system_exit",
        stderr="stderr_system_exit",
    )
    mock_reload_config.assert_called_once()  # only at application startup
    mock_clear_caches_before_each_call.assert_called_once()


def test_automation_reloads_if_necessary(mocker: MockerFixture, cache: Cache) -> None:
    mock_reload_config = mocker.MagicMock()
    mock_clear_caches_before_each_call = mocker.MagicMock()
    with _make_test_client(
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
    loaded_config = LoadedConfigFragment()
    with _make_test_client(
        _DummyAutomationEngineSuccess(),
        cache,
        lambda plugins: LoadingResult(
            loaded_config=loaded_config, config_cache=ConfigCache(loaded_config)
        ),
        lambda ruleset_matcher: None,
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
        plugins=None,
        loading_result=None,
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
        plugins=None,
        loading_result=None,
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
        plugins=None,
        loading_result=None,
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

    @override
    async def __aenter__(self) -> None:
        self.counter += 1
        return await super().__aenter__()
