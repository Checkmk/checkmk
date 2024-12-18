#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time

from fakeredis import FakeRedis
from fastapi.testclient import TestClient

from cmk.base.automation_helper._app import AutomationEngine, AutomationPayload, get_application
from cmk.base.automation_helper._cache import Cache
from cmk.base.automations import AutomationExitCode


class _DummyAutomationEngineSuccess:
    def execute(self, cmd: str, args: list[str], *, reload_config: bool) -> AutomationExitCode:
        return AutomationExitCode.SUCCESS


class _DummyAutomationEngineFailure:
    def execute(self, cmd: str, args: list[str], *, reload_config: bool) -> AutomationExitCode:
        raise SystemExit(1)


_EXAMPLE_AUTOMATION_PAYLOAD = AutomationPayload(
    name="dummy", args=[], stdin="", log_level=logging.INFO
).model_dump()


def _get_test_client(engine: AutomationEngine) -> TestClient:
    """Helper for fetching fastapi test client."""
    cache = Cache.setup(client=FakeRedis())
    app = get_application(
        engine=engine,
        cache=cache,
        reload_config=lambda: None,
    )
    return TestClient(app)


def test_automation_with_success() -> None:
    with _get_test_client(_DummyAutomationEngineSuccess()) as client:
        resp = client.post("/automation", json=_EXAMPLE_AUTOMATION_PAYLOAD)

    assert resp.status_code == 200
    assert resp.json() == {"exit_code": AutomationExitCode.SUCCESS, "output": ""}


def test_automation_with_failure() -> None:
    with _get_test_client(_DummyAutomationEngineFailure()) as client:
        resp = client.post("/automation", json=_EXAMPLE_AUTOMATION_PAYLOAD)

    assert resp.status_code == 200
    assert resp.json() == {"exit_code": 1, "output": ""}


def test_health_check() -> None:
    with _get_test_client(_DummyAutomationEngineSuccess()) as client:
        resp = client.get("/health")

    last_reload_at = resp.json()["last_reload_at"]

    assert resp.status_code == 200
    assert last_reload_at and last_reload_at < time.time()
