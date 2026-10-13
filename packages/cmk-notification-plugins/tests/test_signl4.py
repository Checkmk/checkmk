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

from cmk.notification_plugins.signl4 import main
from cmk.testlib.notification_plugins import exit_code, explicit_password

WEBHOOK_URL: Final = "https://connect.signl4.com/webhook/team-secret"

TEAM_SECRET: Final = explicit_password("PARAMETER_PASSWORD", "team-secret")

SERVICE_CONTEXT: Final = {
    **TEAM_SECRET,
    "WHAT": "SERVICE",
    "NOTIFICATIONTYPE": "PROBLEM",
    "HOSTNAME": "myhost",
    "HOSTSTATE": "UP",
    "HOSTPROBLEMID": "0",
    "SERVICEDESC": "CPU load",
    "SERVICESTATE": "CRITICAL",
    "SERVICEOUTPUT": "Load too high",
    "SERVICEPROBLEMID": "7",
    "CONTACTNAME": "jdoe",
    "CONTACTALIAS": "John Doe",
    "CONTACTEMAIL": "jdoe@example.com",
    "CONTACTPAGER": "+49 170 1234",
    "SHORTDATETIME": "2026-10-07 12:00:00",
}

HOST_CONTEXT: Final = {
    **TEAM_SECRET,
    "WHAT": "HOST",
    "NOTIFICATIONTYPE": "PROBLEM",
    "HOSTNAME": "myhost",
    "HOSTSTATE": "DOWN",
    "HOSTPROBLEMID": "42",
}


def _sent_alert() -> Mapping[str, object]:
    body = responses.calls[0].request.body
    assert isinstance(body, bytes)
    alert: Mapping[str, object] = json.loads(body)
    return alert


@responses.activate
def test_service_problem_alert(notify_context: Callable[[Mapping[str, str]], None]) -> None:
    responses.post(WEBHOOK_URL, json={"eventId": "evt-1"})
    notify_context(SERVICE_CONTEXT)

    exit_code(main)

    assert _sent_alert() == {
        "Title": "PROBLEM on myhost (CPU load)",
        "HostName": "myhost",
        "NotificationType": "PROBLEM",
        "ServiceState": "CRITICAL",
        "ServiceDescription": "CPU load",
        "ServiceOutput": "Load too high",
        "HostState": "UP",
        "NotificationComment": "",
        "ContactName": "jdoe",
        "ContactAlias": "John Doe",
        "ContactEmail": "jdoe@example.com",
        "ContactPager": "+491701234",
        "HostProblemId": "0",
        "ServiceProblemId": "7",
        "DateTime": "2026-10-07 12:00:00",
        "X-S4-SourceSystem": "Checkmk",
        "X-S4-ExternalID": "Checkmk: myhost-0-7:ServiceDesc:Q1BVIGxvYWQ=",
        "X-S4-Status": "new",
    }


_HOST_ACK_CONTEXT: Final = {**HOST_CONTEXT, "NOTIFICATIONTYPE": "ACKNOWLEDGEMENT"}
_SERVICE_ACK_CONTEXT: Final = {**SERVICE_CONTEXT, "NOTIFICATIONTYPE": "ACKNOWLEDGEMENT"}


# fmt: off
@pytest.mark.parametrize(
    "context, title",
    [
        pytest.param(HOST_CONTEXT, "PROBLEM on myhost (DOWN)", id="host_problem"),
        pytest.param(_HOST_ACK_CONTEXT, "ACKNOWLEDGEMENT on myhost ()", id="host_other_event"),
        pytest.param(_SERVICE_ACK_CONTEXT, "ACKNOWLEDGEMENT on myhost (CPU load)", id="service_other_event"),
    ],
)
# fmt: on
@responses.activate
def test_alert_title(
    notify_context: Callable[[Mapping[str, str]], None], context: Mapping[str, str], title: str
) -> None:
    responses.post(WEBHOOK_URL, json={"eventId": "evt-1"})
    notify_context(context)

    exit_code(main)

    assert _sent_alert()["Title"] == title


@pytest.mark.parametrize(
    "notification_type, status",
    [("PROBLEM", "new"), ("ACKNOWLEDGEMENT", "new"), ("RECOVERY", "resolved")],
)
@responses.activate
def test_alert_status(
    notify_context: Callable[[Mapping[str, str]], None], notification_type: str, status: str
) -> None:
    responses.post(WEBHOOK_URL, json={"eventId": "evt-1"})
    notify_context({**HOST_CONTEXT, "NOTIFICATIONTYPE": notification_type})

    exit_code(main)

    assert _sent_alert()["X-S4-Status"] == status


_UNRESOLVED_PROBLEM_ID: Final = {**SERVICE_CONTEXT, "SERVICEPROBLEMID": "$SERVICEPROBLEMID$"}


# fmt: off
@pytest.mark.parametrize(
    "context, external_id",
    [
        pytest.param(HOST_CONTEXT, "Checkmk: myhost-42-", id="host"),
        pytest.param(_UNRESOLVED_PROBLEM_ID, "Checkmk: myhost-0-:ServiceDesc:Q1BVIGxvYWQ=", id="unresolved_problem_id"),
    ],
)
# fmt: on
@responses.activate
def test_alert_external_id(
    notify_context: Callable[[Mapping[str, str]], None],
    context: Mapping[str, str],
    external_id: str,
) -> None:
    responses.post(WEBHOOK_URL, json={"eventId": "evt-1"})
    notify_context(context)

    exit_code(main)

    assert _sent_alert()["X-S4-ExternalID"] == external_id


# fmt: off
@pytest.mark.parametrize(
    "status, reply, expected_exit_code, error",
    [
        pytest.param(HTTPStatus.CREATED, '{"eventId": "evt-1"}', 0, "eventId: evt-1\n201: Created\n", id="ok"),
        pytest.param(HTTPStatus.BAD_REQUEST, "bad", 2, "Error: bad\n400: Bad Request\n", id="client_error"),
        pytest.param(HTTPStatus.BAD_GATEWAY, "down", 1, "Server-Error: down\n502: Bad Gateway\n", id="server_error"),
    ],
)
# fmt: on
@responses.activate
def test_response_maps_to_exit_code(
    notify_context: Callable[[Mapping[str, str]], None],
    capsys: pytest.CaptureFixture[str],
    status: HTTPStatus,
    reply: str,
    expected_exit_code: int,
    error: str,
) -> None:
    responses.post(WEBHOOK_URL, status=status, body=reply)
    notify_context(HOST_CONTEXT)

    assert exit_code(main) == expected_exit_code
    assert capsys.readouterr().err == error
