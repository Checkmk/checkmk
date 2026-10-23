#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Callable, Mapping
from http import HTTPStatus
from typing import Final

import pytest
import responses
from responses import matchers

from cmk.notification_plugins.ilert import main
from cmk.testlib.notification_plugins import exit_code, explicit_password

EVENTS_URL: Final = "https://api.ilert.com/api/v1/events/checkmk-ext/alert-source-key"

CONTEXT: Final = {
    **explicit_password("PARAMETER_ILERT_API_KEY", "alert-source-key"),
    "WHAT": "HOST",
    "NOTIFICATIONTYPE": "PROBLEM",
    "HOSTNAME": "myhost",
    "HOSTSHORTSTATE": "DOWN",
    "PREVIOUSHOSTHARDSHORTSTATE": "UP",
}


@responses.activate
def test_posts_complete_context_as_event(
    notify_context: Callable[[Mapping[str, str]], None],
) -> None:
    responses.post(
        EVENTS_URL,
        json={"incidentKey": "inc-1"},
        match=[
            matchers.header_matcher(
                {
                    "Content-type": "application/json",
                    "Accept": "application/json",
                    "Agent": "checkmk/extension/1.0",
                }
            )
        ],
    )
    notify_context(CONTEXT)

    assert exit_code(main) == 0
    body = responses.calls[0].request.body
    assert isinstance(body, bytes)
    assert json.loads(body) == {**CONTEXT, "EVENT_TXT": "UP -> DOWN"}


_NONE_OPEN: Final = '{"code": "NONE_OPEN_FOR_KEY"}'


# fmt: off
@pytest.mark.parametrize(
    "status, reply, expected_exit_code, outcome",
    [
        pytest.param(200, '{"incidentKey": "inc-1"}', 0, "incidentKey: inc-1", id="accepted"),
        pytest.param(300, "moved", 2, "Error: moved", id="3xx"),
        pytest.param(400, _NONE_OPEN, 0, f"Event already closed in iLert: {_NONE_OPEN}", id="already_closed"),
        pytest.param(400, '{"code": "INVALID"}', 2, 'Event not accepted by iLert: {"code": "INVALID"}', id="rejected"),
        pytest.param(429, "slow down", 1, "Too many requests, will try again. Server response: slow down", id="throttled"),
        pytest.param(451, "nope", 2, "Event not accepted by iLert: nope", id="other_4xx"),
        pytest.param(503, "down", 1, "Server error: down", id="5xx"),
    ],
)
# fmt: on
@responses.activate
def test_response_maps_to_exit_code(
    notify_context: Callable[[Mapping[str, str]], None],
    capsys: pytest.CaptureFixture[str],
    status: int,
    reply: str,
    expected_exit_code: int,
    outcome: str,
) -> None:
    responses.post(EVENTS_URL, status=status, body=reply)
    notify_context(CONTEXT)

    assert exit_code(main) == expected_exit_code
    assert capsys.readouterr().err == f"{outcome}\n{status}: {HTTPStatus(status).phrase}\n"
