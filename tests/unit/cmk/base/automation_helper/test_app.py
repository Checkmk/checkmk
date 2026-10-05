#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import asyncio
import logging
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from http import HTTPStatus
from pathlib import Path
from typing import NoReturn, override

import fakeredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from starlette import status

from cmk.automations.internal import AutomationID, AutomationResult
from cmk.automations.models.helper import AutomationPayload, AutomationResponse
from cmk.base.automation_helper._app import (
    _reloader_task,
    _State,
    AutomationEngine,
    HealthCheckResponse,
    make_application,
)
from cmk.base.automation_helper._cache import Cache, CacheError
from cmk.base.automation_helper._config import Config, ReloaderConfig, ServerConfig, WatcherConfig
from cmk.base.automations.automations import AutomationError
from tests.testlib.common.utils import wait_until


class _DummyAutomationResult(AutomationResult):
    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("dummy")

    @override
    def serialize(self, for_cmk_version: str) -> str:
        return "dummy_serialized"


class _DummyAutomationEngineSuccess:
    def update(
        self,
        omd_root: Path,
        raw_config: Mapping[str, object],
    ) -> None:
        pass

    def execute(
        self,
        cmd: str,  # noqa: ARG002
        args: list[str],  # noqa: ARG002
    ) -> _DummyAutomationResult:
        sys.stdout.write("stdout_success")
        sys.stderr.write("stderr_success")
        return _DummyAutomationResult()


class _DummyAutomationEngineFailure:
    def update(
        self,
        omd_root: Path,
        raw_config: Mapping[str, object],
    ) -> None:
        pass

    def execute(
        self,
        cmd: str,  # noqa: ARG002
        args: list[str],  # noqa: ARG002
    ) -> AutomationError:
        sys.stdout.write("stdout_failure")
        sys.stderr.write("stderr_failure")
        return AutomationError.KNOWN_ERROR


class _DummyAutomationEngineSystemExit:
    def update(
        self,
        omd_root: Path,
        raw_config: Mapping[str, object],
    ) -> None:
        pass

    def execute(
        self,
        cmd: str,  # noqa: ARG002
        args: list[str],  # noqa: ARG002
    ) -> AutomationError:
        sys.stdout.write("stdout_system_exit")
        sys.stderr.write("stderr_system_exit")
        raise SystemExit(1)


class _RecordingAutomationEngine(_DummyAutomationEngineSuccess):
    def __init__(self) -> None:
        self.updates: list[tuple[Path, Mapping[str, object]]] = []

    @override
    def update(self, omd_root: Path, raw_config: Mapping[str, object]) -> None:
        self.updates.append((omd_root, raw_config))


_EXAMPLE_AUTOMATION_PAYLOAD = AutomationPayload(
    name=AutomationID("dummy"), args=[], stdin="", log_level=logging.INFO
).model_dump()


def _make_test_client(
    engine: AutomationEngine,
    cache: Cache,
    reload_config: Callable[[], Mapping[str, object]],
    reloader_config: ReloaderConfig = ReloaderConfig(
        active=True,
        poll_interval=1.0,
        cooldown_interval=5.0,
    ),
) -> TestClient:
    dev_null = Path("/dev/null")
    config = Config(
        server_config=ServerConfig(
            unix_socket_path=dev_null,
            unix_socket_permissions=0,
            pid_file=dev_null,
            access_log=dev_null,
            error_log=dev_null,
            worker_log=dev_null,
            num_workers=0,
        ),
        watcher_config=WatcherConfig(schedules=[]),
        reloader_config=reloader_config,
    )
    return TestClient(
        make_application(
            omd_root=dev_null,
            engine=engine,
            cache=cache,
            config=config,
            reload_config=reload_config,
        )
    )


def test_reloader_is_running(mocker: MockerFixture, cache: Cache) -> None:
    mock_reload_config = mocker.MagicMock()
    with _make_test_client(
        _DummyAutomationEngineSuccess(),
        cache,
        mock_reload_config,
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
            lambda: (
                HealthCheckResponse.model_validate(client.get("/health").json()).last_reload_at
                > current_last_reload_at
            ),
            timeout=0.25,
            interval=0.025,
        )

    assert (
        # once at application startup, once by the reloader task
        mock_reload_config.call_count == 2
    )


def test_automation_with_success(mocker: MockerFixture, cache: Cache) -> None:
    mock_reload_config = mocker.MagicMock()
    with _make_test_client(
        _DummyAutomationEngineSuccess(),
        cache,
        mock_reload_config,
    ) as client:
        resp = client.post("/automation", json=_EXAMPLE_AUTOMATION_PAYLOAD)

    assert resp.status_code == HTTPStatus.OK
    assert AutomationResponse.model_validate(resp.json()) == AutomationResponse(
        serialized_result_or_error_code="dummy_serialized",
        stdout="stdout_success",
        stderr="stderr_success",
    )
    mock_reload_config.assert_called_once()  # only at application startup


def test_automation_with_failure(mocker: MockerFixture, cache: Cache) -> None:
    mock_reload_config = mocker.MagicMock()
    with _make_test_client(
        _DummyAutomationEngineFailure(),
        cache,
        mock_reload_config,
    ) as client:
        resp = client.post("/automation", json=_EXAMPLE_AUTOMATION_PAYLOAD)

    assert resp.status_code == HTTPStatus.OK
    assert AutomationResponse.model_validate(resp.json()) == AutomationResponse(
        serialized_result_or_error_code=1,
        stdout="stdout_failure",
        stderr="stderr_failure",
    )
    mock_reload_config.assert_called_once()  # only at application startup


def test_automation_with_system_exit(mocker: MockerFixture, cache: Cache) -> None:
    mock_reload_config = mocker.MagicMock()
    with _make_test_client(
        _DummyAutomationEngineSystemExit(),
        cache,
        mock_reload_config,
    ) as client:
        resp = client.post("/automation", json=_EXAMPLE_AUTOMATION_PAYLOAD)

    assert resp.status_code == HTTPStatus.OK
    assert AutomationResponse.model_validate(resp.json()) == AutomationResponse(
        serialized_result_or_error_code=1,
        stdout="stdout_system_exit",
        stderr='stderr_system_exit[ERROR] Encountered SystemExit exception while processing automation "dummy" with args: []\n',
    )
    mock_reload_config.assert_called_once()  # only at application startup


def test_automation_reloads_if_necessary(mocker: MockerFixture, cache: Cache) -> None:
    mock_reload_config = mocker.MagicMock()
    with _make_test_client(
        _DummyAutomationEngineSuccess(),
        cache,
        mock_reload_config,
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


def test_reloaded_configuration_reaches_the_engine(mocker: MockerFixture, cache: Cache) -> None:
    initial, reloaded = mocker.MagicMock(), mocker.MagicMock()
    engine = _RecordingAutomationEngine()
    with _make_test_client(
        engine,
        cache,
        mocker.MagicMock(side_effect=[initial, reloaded]),
    ) as client:
        cache.store_last_detected_change(time.time())
        client.post("/automation", json=_EXAMPLE_AUTOMATION_PAYLOAD)

    assert [raw_config for _omd_root, raw_config in engine.updates] == [initial, reloaded]


def test_failed_first_load_is_retried_and_reported(mocker: MockerFixture, cache: Cache) -> None:
    raw_config = mocker.MagicMock()
    engine = _RecordingAutomationEngine()
    with _make_test_client(
        engine,
        cache,
        mocker.MagicMock(
            side_effect=[RuntimeError("broken config"), RuntimeError("broken config"), raw_config]
        ),
        # Only the automations may reload here; no change is ever recorded in the cache.
        reloader_config=ReloaderConfig(active=False, poll_interval=1.0, cooldown_interval=5.0),
    ) as client:
        first = AutomationResponse.model_validate(
            client.post("/automation", json=_EXAMPLE_AUTOMATION_PAYLOAD).json()
        )
        second = AutomationResponse.model_validate(
            client.post("/automation", json=_EXAMPLE_AUTOMATION_PAYLOAD).json()
        )

    assert first.stderr == "Error reloading configuration: broken config"
    assert second.serialized_result_or_error_code == "dummy_serialized"
    assert [raw_config for _omd_root, raw_config in engine.updates] == [raw_config]


def test_health_check(cache: Cache) -> None:
    with _make_test_client(
        _DummyAutomationEngineSuccess(),
        cache,
        dict,
    ) as client:
        resp = client.get("/health")

    assert resp.status_code == HTTPStatus.OK
    assert HealthCheckResponse.model_validate(resp.json()).last_reload_at < time.time()


@pytest.mark.asyncio
async def test_reloader_single_change(mocker: MockerFixture, cache: Cache) -> None:
    mock_reload_callback = mocker.MagicMock()
    state = _State(
        last_reload_at=1,
        engine=_DummyAutomationEngineSuccess(),
        omd_root=Path("/dev/null"),
        reload_config=mock_reload_callback,
        changes_cache=cache,
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
            state=state,
            delayer_factory=lambda delay: _mock_delay(mock_delay_state, delay),
            logger=logging.getLogger(),
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
        engine=_DummyAutomationEngineSuccess(),
        omd_root=Path("/dev/null"),
        reload_config=mock_reload_callback,
        changes_cache=cache,
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
            state=state,
            delayer_factory=lambda delay: _mock_delay(mock_delay_state, delay),
            logger=logging.getLogger(),
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
async def test_reloader_takes_state_into_account(mocker: MockerFixture) -> None:
    mock_reload_callback = mocker.MagicMock()
    cache = _RecordingCache.setup(client=fakeredis.FakeRedis())
    state = _State(
        last_reload_at=1,
        engine=_DummyAutomationEngineSuccess(),
        omd_root=Path("/dev/null"),
        reload_config=mock_reload_callback,
        changes_cache=cache,
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
            state=state,
            delayer_factory=lambda delay: _mock_delay(mock_delay_state, delay),
            logger=logging.getLogger(),
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
    assert cache.reload_decisions == [3]


def _make_state(cache: Cache) -> _State:
    return _State(
        engine=_DummyAutomationEngineSuccess(),
        omd_root=Path("/dev/null"),
        reload_config=lambda: pytest.fail("unexpected reload"),
        last_reload_at=0,
        changes_cache=cache,
    )


@pytest.mark.asyncio
async def test_exclusive_rejects_overlapping_work(cache: Cache) -> None:
    state = _make_state(cache)

    with (
        state.exclusive(),
        pytest.raises(RuntimeError, match="must not overlap"),
        state.exclusive(),
    ):
        pass


@pytest.mark.asyncio
async def test_exclusive_rejects_work_off_the_event_loop_thread(cache: Cache) -> None:
    state = _make_state(cache)

    def enter_exclusive() -> None:
        with state.exclusive():
            pass

    with pytest.raises(RuntimeError, match="must run on the event loop thread"):
        await asyncio.to_thread(enter_exclusive)


@pytest.mark.asyncio
async def test_exclusive_is_released_after_failed_work(cache: Cache) -> None:
    state = _make_state(cache)

    with pytest.raises(ValueError), state.exclusive():
        raise ValueError

    with state.exclusive():
        pass


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


@dataclass(frozen=True)
class _RecordingCache(Cache):
    """A cache that records the last reload time of every reload decision."""

    reload_decisions: list[float] = field(default_factory=list)

    @override
    def reload_required(self, last_reload: float) -> bool:
        self.reload_decisions.append(last_reload)
        return super().reload_required(last_reload)


class FailingCache(Cache):
    """A cache that always raises CacheError."""

    @override
    def get_last_detected_change(self) -> NoReturn:
        raise CacheError("Failed to connect to Redis")


def test_automation_cache_error_on_stale_config() -> None:
    """Test that a CacheError during reload_required is handled gracefully.

    When Redis is unavailable, reload_required returns True (force reload) instead
    of propagating CacheError. The automation should succeed, not return a 503.
    """

    with _make_test_client(
        _DummyAutomationEngineSuccess(),
        FailingCache(fakeredis.FakeRedis()),
        dict,
    ) as client:
        resp = client.post("/automation", json=_EXAMPLE_AUTOMATION_PAYLOAD)

    assert resp.status_code == status.HTTP_200_OK
    assert AutomationResponse.model_validate(resp.json()) == AutomationResponse(
        serialized_result_or_error_code="dummy_serialized",
        stdout="stdout_success",
        stderr="stderr_success",
    )


def _guard_is_held(state: _State) -> bool:
    try:
        with state.exclusive():
            return False
    except RuntimeError as error:
        if "must not overlap" in str(error):
            return True
        raise


def _state_of(client: TestClient) -> _State:
    assert isinstance(client.app, FastAPI)
    state: _State = client.app.state.dependencies.state
    return state


class _GuardProbingEngine:
    def __init__(self) -> None:
        self.state: _State | None = None
        self.guard_held: list[bool] = []

    def update(
        self,
        omd_root: Path,
        raw_config: Mapping[str, object],
    ) -> None:
        pass

    def execute(
        self,
        cmd: str,  # noqa: ARG002
        args: list[str],  # noqa: ARG002
    ) -> _DummyAutomationResult:
        assert self.state is not None
        self.guard_held.append(_guard_is_held(self.state))
        return _DummyAutomationResult()


def test_automation_runs_under_the_guard(mocker: MockerFixture, cache: Cache) -> None:
    engine = _GuardProbingEngine()
    client = _make_test_client(
        engine,
        cache,
        mocker.MagicMock(),
    )
    engine.state = _state_of(client)

    with client:
        client.post("/automation", json=_EXAMPLE_AUTOMATION_PAYLOAD)

    assert engine.guard_held == [True]


def test_initial_load_runs_under_the_guard(mocker: MockerFixture, cache: Cache) -> None:
    guard_held: list[bool] = []

    def reload_config() -> Mapping[str, object]:
        guard_held.append(_guard_is_held(state))
        raw_config: Mapping[str, object] = mocker.MagicMock()
        return raw_config

    client = _make_test_client(
        _DummyAutomationEngineSuccess(),
        cache,
        reload_config,
    )
    state = _state_of(client)

    with client:
        pass

    assert guard_held == [True]


@pytest.mark.asyncio
async def test_reload_by_the_reloader_runs_under_the_guard(
    mocker: MockerFixture, cache: Cache
) -> None:
    guard_held: list[bool] = []

    def reload_config() -> Mapping[str, object]:
        guard_held.append(_guard_is_held(state))
        raw_config: Mapping[str, object] = mocker.MagicMock()
        return raw_config

    state = _State(
        engine=_DummyAutomationEngineSuccess(),
        omd_root=Path("/dev/null"),
        last_reload_at=1,
        reload_config=reload_config,
        changes_cache=cache,
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
            state=state,
            delayer_factory=lambda delay: _mock_delay(mock_delay_state, delay),
            logger=logging.getLogger(),
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
    assert guard_held == [True]


class _CrashingCache(Cache):
    """A cache that fails in a way the reloader does not handle."""

    @override
    def get_last_detected_change(self) -> NoReturn:
        raise ValueError("unexpected failure")


def test_reloader_crash_is_logged(mocker: MockerFixture, caplog: pytest.LogCaptureFixture) -> None:
    def reloader_crash_logged() -> bool:
        return any(
            record.levelno == logging.CRITICAL and record.getMessage() == "Reloader stopped"
            for record in caplog.records
        )

    with _make_test_client(
        _DummyAutomationEngineSuccess(),
        _CrashingCache(fakeredis.FakeRedis()),
        mocker.MagicMock(),
        reloader_config=ReloaderConfig(
            active=True,
            poll_interval=0.0,
            cooldown_interval=0.0,
        ),
    ):
        wait_until(reloader_crash_logged, timeout=1, interval=0.01)

    assert reloader_crash_logged()
