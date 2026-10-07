#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping
from typing import Final
from urllib.parse import parse_qs, urlsplit

import pytest
import requests
import responses
from requests.exceptions import ProxyError

from cmk.notification_plugins.pushover import main

API_URL: Final = "https://api.pushover.net/1/messages.json"

HOST_CONTEXT: Final = {
    "WHAT": "HOST",
    "NOTIFICATIONTYPE": "PROBLEM",
    "HOSTNAME": "myhost",
    "HOSTSHORTSTATE": "DOWN",
    "PREVIOUSHOSTHARDSHORTSTATE": "UP",
    "HOSTOUTPUT": "Host unreachable",
    "MICROTIME": "1700000000123456",
    "PARAMETER_API_KEY": "app-token",
    "PARAMETER_RECIPIENT_KEY": "user-key",
}

SERVICE_CONTEXT: Final = {
    **HOST_CONTEXT,
    "WHAT": "SERVICE",
    "SERVICEDESC": "CPU load",
    "SERVICESHORTSTATE": "CRIT",
    "PREVIOUSSERVICEHARDSHORTSTATE": "OK",
    "SERVICEOUTPUT": "Load too high",
}

LINK_CONTEXT: Final = {
    "PARAMETER_URL_PREFIX_1": "automatic_https",
    "MONITORING_HOST": "monitoring.lan",
    "OMD_SITE": "mysite",
    "HOSTURL": "/view?host=myhost",
    "SERVICEURL": "/view?service=cpu",
}


def _sent_params() -> dict[str, list[str]]:
    return parse_qs(urlsplit(str(responses.calls[0].request.url)).query)


@responses.activate
def test_sends_notification_with_credentials_and_timestamp(
    notify_context: Callable[[Mapping[str, str]], None],
) -> None:
    responses.post(API_URL, json={"status": 1})
    notify_context(HOST_CONTEXT)

    assert main() == 0

    params = _sent_params()
    assert {key: params[key] for key in ("token", "user", "timestamp", "html")} == {
        "token": ["app-token"],
        "user": ["user-key"],
        "timestamp": ["1700000000"],
        "html": ["1"],
    }


# fmt: off
@pytest.mark.parametrize(
    "context, notification_type, title",
    [
        pytest.param(HOST_CONTEXT, "PROBLEM", "myhost UP → DOWN", id="host_problem"),
        pytest.param(SERVICE_CONTEXT, "PROBLEM", "myhost/CPU load OK → CRIT", id="service_problem"),
        pytest.param(HOST_CONTEXT, "FLAPPINGSTART", "myhost Started Flapping", id="flapping_start"),
        pytest.param(HOST_CONTEXT, "FLAPPINGSTOP", "myhost Stopped Flapping (DOWN)", id="flapping_stop"),
        pytest.param(HOST_CONTEXT, "DOWNTIMECANCELLED", "myhost Downtime Cancelled (DOWN)", id="downtime"),
        pytest.param(SERVICE_CONTEXT, "ACKNOWLEDGEMENT", "myhost/CPU load Acknowledged (CRIT)", id="acknowledgement"),
        pytest.param(HOST_CONTEXT, "CUSTOM", "myhost Custom Notification (DOWN)", id="custom"),
        pytest.param(HOST_CONTEXT, "ALERTHANDLER (0)", "myhost ALERTHANDLER (0)", id="other"),
    ],
)
# fmt: on
@responses.activate
def test_title_describes_event(
    notify_context: Callable[[Mapping[str, str]], None],
    context: Mapping[str, str],
    notification_type: str,
    title: str,
) -> None:
    responses.post(API_URL, json={"status": 1})
    notify_context({**context, "NOTIFICATIONTYPE": notification_type})

    main()

    assert _sent_params()["title"] == [title]


_HOST_LINK: Final = '<a href="https://monitoring.lan/mysite/view?host=myhost">myhost</a>'
_SERVICE_LINK: Final = '<a href="https://monitoring.lan/mysite/view?service=cpu">CPU load</a>'
_LINKED_HOST: Final = {**HOST_CONTEXT, **LINK_CONTEXT}
_LINKED_SERVICE: Final = {**SERVICE_CONTEXT, **LINK_CONTEXT}


# fmt: off
@pytest.mark.parametrize(
    "context, message",
    [
        pytest.param(HOST_CONTEXT, "Host unreachable", id="host_without_link"),
        pytest.param(_LINKED_HOST, f"Host unreachable <i>Link: </i>{_HOST_LINK}", id="host_with_link"),
        pytest.param(_LINKED_SERVICE, f"Load too high <i>Link: </i>{_HOST_LINK}{_SERVICE_LINK}", id="service_with_links"),
    ],
)
# fmt: on
@responses.activate
def test_message_contains_output_and_links(
    notify_context: Callable[[Mapping[str, str]], None], context: Mapping[str, str], message: str
) -> None:
    responses.post(API_URL, json={"status": 1})
    notify_context(context)

    main()

    assert _sent_params()["message"] == [message]


def _sent_priority_params(
    notify_context: Callable[[Mapping[str, str]], None], parameters: Mapping[str, str]
) -> dict[str, list[str]]:
    responses.post(API_URL, json={"status": 1})
    notify_context({**HOST_CONTEXT, **parameters})

    main()

    params = _sent_params()
    return {
        key: params[key] for key in ("priority", "retry", "expire", "receipts") if key in params
    }


@pytest.mark.parametrize(
    "parameters, expected",
    [
        pytest.param({}, {}, id="unset"),
        pytest.param({"PARAMETER_PRIORITY_1": "high"}, {"priority": ["1"]}, id="high"),
        pytest.param({"PARAMETER_PRIORITY_1": "lowest"}, {"priority": ["-2"]}, id="lowest"),
        pytest.param({"PARAMETER_PRIORITY_1": "unknown"}, {}, id="unknown_ignored"),
    ],
)
@responses.activate
def test_priority_parameters(
    notify_context: Callable[[Mapping[str, str]], None],
    parameters: Mapping[str, str],
    expected: Mapping[str, list[str]],
) -> None:
    assert _sent_priority_params(notify_context, parameters) == expected


_EMERGENCY: Final = {
    "PARAMETER_PRIORITY_1": "emergency",
    "PARAMETER_PRIORITY_2_1": "60.0",
    "PARAMETER_PRIORITY_2_2": "3600.0",
}


@responses.activate
def test_emergency_priority_sends_retry_and_expire(
    notify_context: Callable[[Mapping[str, str]], None],
) -> None:
    assert _sent_priority_params(notify_context, _EMERGENCY) == {
        "priority": ["2"],
        "retry": ["60"],
        "expire": ["3600"],
    }


@responses.activate
def test_emergency_priority_sends_receipts_url(
    notify_context: Callable[[Mapping[str, str]], None],
) -> None:
    parameters = {**_EMERGENCY, "PARAMETER_PRIORITY_2_3": "https://receipts.example.com"}

    assert _sent_priority_params(notify_context, parameters)["receipts"] == [
        "https://receipts.example.com"
    ]


@pytest.mark.parametrize(
    "parameters, sound",
    [
        pytest.param({}, None, id="unset"),
        pytest.param({"PARAMETER_SOUND": "none"}, None, id="none"),
        pytest.param({"PARAMETER_SOUND": "siren"}, ["siren"], id="siren"),
    ],
)
@responses.activate
def test_sound_parameter(
    notify_context: Callable[[Mapping[str, str]], None],
    parameters: Mapping[str, str],
    sound: list[str] | None,
) -> None:
    responses.post(API_URL, json={"status": 1})
    notify_context({**HOST_CONTEXT, **parameters})

    main()

    assert _sent_params().get("sound") == sound


_API_ERROR: Final = '{"status": 0, "errors": ["invalid"]}'


# fmt: off
@pytest.mark.parametrize(
    "status, body, output",
    [
        pytest.param(400, "rejected", "Failed to send notification. Status: 400, Response: rejected\n", id="http_error"),
        pytest.param(200, "not json", "Failed to decode JSON response: not json\n", id="invalid_json"),
        pytest.param(200, _API_ERROR, f"Received an error from the Pushover API: {_API_ERROR}", id="api_error"),
    ],
)
# fmt: on
@responses.activate
def test_unsuccessful_response_fails(
    notify_context: Callable[[Mapping[str, str]], None],
    capsys: pytest.CaptureFixture[str],
    status: int,
    body: str,
    output: str,
) -> None:
    responses.post(API_URL, status=status, body=body)
    notify_context(HOST_CONTEXT)

    assert main() == 1
    assert capsys.readouterr().out == output


# fmt: off
@pytest.mark.parametrize(
    "error, output",
    [
        pytest.param(ProxyError(), "Cannot connect to proxy: http://***@proxy.lan:3128\n", id="proxy"),
        pytest.param(requests.ConnectionError(), f"POST request to server failed: {API_URL}\n", id="connection"),
    ],
)
# fmt: on
@responses.activate
def test_connection_failure_fails(
    notify_context: Callable[[Mapping[str, str]], None],
    capsys: pytest.CaptureFixture[str],
    error: requests.exceptions.RequestException,
    output: str,
) -> None:
    responses.post(API_URL, body=error)
    notify_context({**HOST_CONTEXT, "PARAMETER_PROXY_URL": "http://user:secret@proxy.lan:3128"})

    assert main() == 1
    assert capsys.readouterr().out == output
