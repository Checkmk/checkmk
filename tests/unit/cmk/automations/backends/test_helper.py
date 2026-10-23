#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
import requests

from cmk.automations.backends.helper import AutomationHelperUnavailable, HelperExecutor
from cmk.automations.internal import AutomationID


class _FakeResponse:
    def raise_for_status(self) -> None:
        pass

    def json(self) -> object:
        return {"serialized_result_or_error_code": "result", "stdout": "", "stderr": ""}


class _FakeSession:
    """Answers a post like the automation helper and records the used socket timeouts

    Legacy compromise: the HTTP transport of the executor is not injectable."""

    def __init__(self, exception: Exception | None = None) -> None:
        self._exception = exception
        self.timeouts: list[float | None] = []

    def post(
        self,
        _url: str,
        json: object,  # noqa: ARG002
        timeout: float | None = None,
    ) -> _FakeResponse:
        self.timeouts.append(timeout)
        if self._exception is not None:
            raise self._exception
        return _FakeResponse()


def _install_session(monkeypatch: pytest.MonkeyPatch, session: _FakeSession) -> None:
    monkeypatch.setattr(
        "cmk.automations.backends.helper.make_unixsocket_session", lambda *_args: session
    )


def test_request_to_the_helper_outlasts_the_timeout_of_the_automation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    _install_session(monkeypatch, session)

    HelperExecutor().execute(AutomationID("restart"), [], "", timeout=100, for_cmk_version="2.4.0")

    assert session.timeouts == [160]


def test_request_to_the_helper_is_unbounded_without_an_automation_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    _install_session(monkeypatch, session)

    HelperExecutor().execute(AutomationID("restart"), [], "", timeout=None, for_cmk_version="2.4.0")

    assert session.timeouts == [None]


def test_helper_that_does_not_answer_in_time_is_reported_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_session(monkeypatch, _FakeSession(exception=requests.ReadTimeout()))

    with pytest.raises(AutomationHelperUnavailable, match="did not answer within 160 seconds"):
        HelperExecutor().execute(
            AutomationID("restart"), [], "", timeout=100, for_cmk_version="2.4.0"
        )
