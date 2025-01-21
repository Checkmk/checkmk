#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time
from collections.abc import Callable

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from cmk.base.automation_helper._app import (
    AutomationEngine,
    AutomationPayload,
    AutomationResponse,
    get_application,
    HealthCheckResponse,
)
from cmk.base.automation_helper._cache import Cache
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
