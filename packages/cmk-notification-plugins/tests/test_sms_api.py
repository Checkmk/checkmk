#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping
from http import HTTPStatus
from typing import Final
from urllib.parse import parse_qs

import pytest
import requests
import responses
from responses import matchers

from cmk.notification_plugins.sms_api import main
from cmk.testlib.notification_plugins import exit_code, explicit_password

MODEM_URL: Final = "https://modem.lan"
LEGACY_URL: Final = f"{MODEM_URL}/cgi-bin/sms_send"
LOGIN_URL: Final = f"{MODEM_URL}/api/login"
SEND_URL: Final = f"{MODEM_URL}/api/messages/actions/send"
HTML_PAGE: Final = "<!DOCTYPE html><html></html>"

CONTEXT: Final = {
    "WHAT": "HOST",
    "NOTIFICATIONTYPE": "PROBLEM",
    "HOSTNAME": "myhost",
    "HOSTSTATE": "DOWN",
    "CONTACTNAME": "jdoe",
    "CONTACTPAGER": "+49 170 1234",
    "PARAMETER_MODEM_TYPE": "trb140",
    "PARAMETER_URL": MODEM_URL,
    "PARAMETER_USERNAME": "admin",
    **explicit_password("PARAMETER_PASSWORD", "secret"),
}

_MANDATORY: Final = ("PARAMETER_MODEM_TYPE", "PARAMETER_URL", "PARAMETER_PASSWORD_1")
_WITHOUT_MANDATORY: Final = {k: v for k, v in CONTEXT.items() if k not in _MANDATORY}
_MANDATORY_MISSING: Final = (
    f"The following mandatory context parameters are not set: {' '.join(_MANDATORY)}\n"
)


# fmt: off
@pytest.mark.parametrize(
    "context, output",
    [
        pytest.param(_WITHOUT_MANDATORY, _MANDATORY_MISSING, id="missing_parameters"),
        pytest.param({**CONTEXT, "CONTACTPAGER": " "}, "Error: Pager Number of jdoe not set\n", id="missing_pager_number"),
        pytest.param({**CONTEXT, "PARAMETER_MODEM_TYPE": "other"}, "Unknown unsupported modem: other", id="unknown_modem"),
    ],
)
# fmt: on
@responses.activate
def test_invalid_configuration_fails_without_request(
    notify_context: Callable[[Mapping[str, str]], None],
    capsys: pytest.CaptureFixture[str],
    context: Mapping[str, str],
    output: str,
) -> None:
    notify_context(context)

    assert exit_code(main) == 2
    assert capsys.readouterr().out == output
    assert not responses.calls


@responses.activate
def test_legacy_endpoint_sends_sms(
    notify_context: Callable[[Mapping[str, str]], None], capsys: pytest.CaptureFixture[str]
) -> None:
    responses.post(LEGACY_URL, body="OK\n")
    notify_context(CONTEXT)

    assert exit_code(main) == 0
    assert capsys.readouterr().out == "Notification successfully sent via sms.\n"
    body = responses.calls[0].request.body
    assert isinstance(body, str)
    assert parse_qs(body) == {
        "username": ["admin"],
        "password": ["secret"],
        "number": ["+491701234"],
        "text": ["'myhost is DOWN'"],
    }


@pytest.mark.parametrize(
    "parameters, timeout",
    [
        pytest.param({}, 10.0, id="default"),
        pytest.param({"PARAMETER_TIMEOUT": "3.5"}, 3.5, id="configured"),
    ],
)
@responses.activate
def test_request_timeout(
    notify_context: Callable[[Mapping[str, str]], None],
    parameters: Mapping[str, str],
    timeout: float,
) -> None:
    responses.post(
        LEGACY_URL, body="OK\n", match=[matchers.request_kwargs_matcher({"timeout": timeout})]
    )
    notify_context({**CONTEXT, **parameters})

    assert exit_code(main) == 0


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="TLS verification is inverted: it is only enabled when PARAMETER_IGNORE_SSL is set",
)
@pytest.mark.parametrize(
    "parameters, verify",
    [
        pytest.param({}, True, id="verified_by_default"),
        pytest.param({"PARAMETER_IGNORE_SSL": "True"}, False, id="ignored_on_request"),
    ],
)
@responses.activate
def test_tls_verification(
    monkeypatch: pytest.MonkeyPatch,
    notify_context: Callable[[Mapping[str, str]], None],
    parameters: Mapping[str, str],
    verify: bool,
) -> None:
    for var in ("REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
        monkeypatch.delenv(var, raising=False)
    responses.post(
        LEGACY_URL, body="OK\n", match=[matchers.request_kwargs_matcher({"verify": verify})]
    )
    notify_context({**CONTEXT, **parameters})

    assert exit_code(main) == 0


_LEGACY_HTTP_ERROR: Final = (
    f"HTTPError sending SMS: 500 Server Error: Internal Server Error for url: {LEGACY_URL}, b'boom'\n"
)


# fmt: off
@pytest.mark.parametrize(
    "status, body, error",
    [
        pytest.param(HTTPStatus.OK, "ERROR\n", "Error Status: 200 Details: b'ERROR\\n'\n", id="rejected"),
        pytest.param(HTTPStatus.INTERNAL_SERVER_ERROR, "boom", _LEGACY_HTTP_ERROR, id="http_error"),
    ],
)
# fmt: on
@responses.activate
def test_legacy_endpoint_failure(
    notify_context: Callable[[Mapping[str, str]], None],
    capsys: pytest.CaptureFixture[str],
    status: HTTPStatus,
    body: str,
    error: str,
) -> None:
    responses.post(LEGACY_URL, status=status, body=body)
    notify_context(CONTEXT)

    assert exit_code(main) == 2
    assert capsys.readouterr().err == error


@responses.activate
def test_unreachable_modem_fails(
    notify_context: Callable[[Mapping[str, str]], None], capsys: pytest.CaptureFixture[str]
) -> None:
    responses.post(LEGACY_URL, body=requests.exceptions.ConnectionError("unreachable"))
    notify_context(CONTEXT)

    assert exit_code(main) == 2
    assert capsys.readouterr().err == "Error sending SMS: unreachable\n"


@responses.activate
def test_api_endpoint_sends_sms_when_legacy_endpoint_is_gone(
    notify_context: Callable[[Mapping[str, str]], None], capsys: pytest.CaptureFixture[str]
) -> None:
    responses.post(LEGACY_URL, body=HTML_PAGE)
    responses.post(
        LOGIN_URL,
        json={"data": {"token": "session-token"}},
        match=[matchers.json_params_matcher({"username": "admin", "password": "secret"})],
    )
    responses.post(
        SEND_URL,
        json={"success": True},
        match=[
            matchers.header_matcher({"Authorization": "Bearer session-token"}),
            matchers.json_params_matcher(
                {"data": {"number": "+491701234", "message": "'myhost is DOWN'", "modem": "3-1"}}
            ),
        ],
    )
    notify_context(CONTEXT)

    assert exit_code(main) == 0
    assert capsys.readouterr().out == "Notification successfully sent via sms.\n"


_NO_TOKEN_ERROR: Final = "Error calling API: Got no session token.\n"
_LOGIN_HTTP_ERROR: Final = (
    f"HTTPError sending SMS: 401 Client Error: Unauthorized for url: {LOGIN_URL}, b'{HTML_PAGE}'\n"
)


# fmt: off
@pytest.mark.parametrize(
    "login_status, login_reply, send_reply, error",
    [
        pytest.param(HTTPStatus.OK, {"data": {}}, {"success": True}, _NO_TOKEN_ERROR, id="no_token"),
        pytest.param(HTTPStatus.OK, {"data": {"token": "session-token"}}, {"success": False}, "", id="not_sent"),
        pytest.param(HTTPStatus.UNAUTHORIZED, {}, {"success": True}, _LOGIN_HTTP_ERROR, id="login_rejected"),
    ],
)
# fmt: on
@responses.activate
def test_api_endpoint_failure(
    notify_context: Callable[[Mapping[str, str]], None],
    capsys: pytest.CaptureFixture[str],
    login_status: HTTPStatus,
    login_reply: Mapping[str, object],
    send_reply: Mapping[str, object],
    error: str,
) -> None:
    responses.post(LEGACY_URL, body=HTML_PAGE)
    responses.post(LOGIN_URL, status=login_status, json=login_reply)
    responses.post(SEND_URL, json=send_reply)
    notify_context(CONTEXT)

    assert exit_code(main) == 2
    assert capsys.readouterr().err == error
