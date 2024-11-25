#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time

from fastapi.testclient import TestClient

from cmk.base import automation_helper
from cmk.base.automations import AutomationExitCode


class DummyAutomationEngineSuccess:
    def execute(self, cmd: str, args: list[str]) -> AutomationExitCode:
        return AutomationExitCode.SUCCESS


class DummyAutomationEngineFailure:
    def execute(self, cmd: str, args: list[str]) -> AutomationExitCode:
        raise SystemExit()


class DummyAutomationEngineTimeout:
    def execute(self, cmd: str, args: list[str]) -> AutomationExitCode:
        time.sleep(1)
        return AutomationExitCode.SUCCESS


EXAMPLE_AUTOMATION_REQUEST = automation_helper.AutomationRequest(
    name="dummy", args=[], stdin="", log_level=logging.INFO
).model_dump()


def get_test_client(*, engine: automation_helper.AutomationEngine) -> TestClient:
    """Helper for fetching fastapi test client."""
    app = automation_helper.get_application(engine=engine, reload_config=lambda: None)
    return TestClient(app)


def test_automation_with_success() -> None:
    client = get_test_client(engine=DummyAutomationEngineSuccess())

    resp = client.post("/automation", json=EXAMPLE_AUTOMATION_REQUEST)

    assert resp.status_code == 200
    assert resp.json() == {"exit_code": AutomationExitCode.SUCCESS, "output": ""}


def test_automation_with_failure() -> None:
    client = get_test_client(engine=DummyAutomationEngineFailure())

    resp = client.post("/automation", json=EXAMPLE_AUTOMATION_REQUEST)

    assert resp.status_code == 200
    assert resp.json() == {"exit_code": AutomationExitCode.SYSTEM_EXIT, "output": ""}


def test_automation_with_timeout() -> None:
    client = get_test_client(engine=DummyAutomationEngineTimeout())
    headers = {"keep-alive": "timeout=0"}

    resp = client.post("/automation", json=EXAMPLE_AUTOMATION_REQUEST, headers=headers)

    assert resp.status_code == 408
    assert resp.json() == {
        "exit_code": AutomationExitCode.TIMEOUT,
        "output": "Timed out after 0 seconds",
    }


def test_health_check() -> None:
    client = get_test_client(engine=DummyAutomationEngineSuccess())

    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"up": True}
