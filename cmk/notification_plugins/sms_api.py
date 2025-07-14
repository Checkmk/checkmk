#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import Callable, NoReturn, Self

import requests

from cmk.utils.http_proxy_config import deserialize_http_proxy_config
from cmk.utils.notify_types import PluginNotificationContext

from cmk.notification_plugins.utils import (
    collect_context,
    get_password_from_env_or_context,
    get_sms_message_from_context,
    quote_message,
)

#   .--Classes-------------------------------------------------------------.
#   |                    ____ _                                            |
#   |                   / ___| | __ _ ___ ___  ___  ___                    |
#   |                  | |   | |/ _` / __/ __|/ _ \/ __|                   |
#   |                  | |___| | (_| \__ \__ \  __/\__ \                   |
#   |                   \____|_|\__,_|___/___/\___||___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


class Errors(list[str]):
    """Class for collected errors."""


Message = str


@dataclass
class RequestParameter:
    """Dataclass for request related context parameter for all modems."""

    recipient: str
    url: str
    verify: bool
    proxies: MutableMapping[str, str] | None
    user: str
    pwd: str
    timeout: float


@dataclass
class Context:
    request_parameter: RequestParameter
    message: Message
    send_function: Callable[[Self], int]


# .
#   .--Context processing--------------------------------------------------.
#   |                   ____            _            _                     |
#   |                  / ___|___  _ __ | |_ _____  _| |_                   |
#   |                 | |   / _ \| '_ \| __/ _ \ \/ / __|                  |
#   |                 | |__| (_) | | | | ||  __/>  <| |_                   |
#   |                  \____\___/|_| |_|\__\___/_/\_\\__|                  |
#   |                                                                      |
#   |                                             _                        |
#   |           _ __  _ __ ___   ___ ___  ___ ___(_)_ __   __ _            |
#   |          | '_ \| '__/ _ \ / __/ _ \/ __/ __| | '_ \ / _` |           |
#   |          | |_) | | | (_) | (_|  __/\__ \__ \ | | | | (_| |           |
#   |          | .__/|_|  \___/ \___\___||___/___/_|_| |_|\__, |           |
#   |          |_|                                        |___/            |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'
def _get_context_parameter(raw_context: PluginNotificationContext) -> Errors | Context:
    """First, get the request parameters for sendind the sms. Then construct
    the sms message and get the endpoint specific parameters to return the
    context for notification processing.
    """
    missing_params: list[str] = []
    for mandatory in [
        "PARAMETER_MODEM_TYPE",
        "PARAMETER_URL",
        "PARAMETER_USERNAME",
        "PARAMETER_PASSWORD_1",
    ]:
        if mandatory not in raw_context:
            missing_params.append(mandatory)

    if missing_params:
        return Errors(
            [
                "The following mandatory context parameters are not set: %s\n"
                % " ".join(missing_params)
            ]
        )

    request_parameter = _get_request_params_from_context(raw_context)

    if isinstance(request_parameter, Errors):
        return request_parameter

    message = quote_message(get_sms_message_from_context(raw_context), max_length=160)

    endpoint = raw_context["PARAMETER_MODEM_TYPE"]
    if endpoint == "trb140":
        return Context(
            request_parameter=request_parameter,
            send_function=_send_func_trb140,
            message=message,
        )

    return Errors(["Unknown unsupported modem: %s" % endpoint])


def _get_request_params_from_context(
    raw_context: PluginNotificationContext,
) -> Errors | RequestParameter:
    recipient = raw_context["CONTACTPAGER"].replace(" ", "")
    if not recipient:
        return Errors(["Error: Pager Number of %s not set\n" % raw_context["CONTACTNAME"]])

    return RequestParameter(
        recipient=recipient,
        url=raw_context["PARAMETER_URL"],
        verify="PARAMETER_IGNORE_SSL" in raw_context,
        proxies=deserialize_http_proxy_config(
            raw_context.get("PARAMETER_PROXY_URL")
        ).to_requests_proxies(),
        user=raw_context["PARAMETER_USERNAME"],
        pwd=get_password_from_env_or_context(
            key="PARAMETER_PASSWORD",
            context=raw_context,
        ),
        timeout=float(raw_context.get("PARAMETER_TIMEOUT", 10.0)),
    )


# .
#   .--Main----------------------------------------------------------------.
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _send_func_trb140(context: Context) -> int:
    """Main processing of notifications for trb140"""
    try:
        response = _trb140_mobile_post(context)
        if "<!doctype html" in response.text.lower():
            return _trb140_api(context)

        response.raise_for_status()

        if response.status_code != 200 or not response.content.startswith(b"OK\n"):
            sys.stderr.write(
                f"Error Status: {response.status_code} Details: {response.content!r}\n"
            )
            return 2

    except requests.exceptions.HTTPError as e:
        sys.stderr.write(f"HTTPError sending SMS: {e}, {response.content!r}\n")
        return 2

    except Exception as e:
        sys.stderr.write(f"Error sending SMS: {e}\n")
        return 2

    sys.stdout.write("Notification successfully sent via sms.\n")
    return 0


def _trb140_api(context: Context) -> int:
    """Since firmware 7.14 the API has to be used"""
    try:
        token_response = requests.post(
            context.request_parameter.url + "/api/login",
            json={
                "username": context.request_parameter.user,
                "password": context.request_parameter.pwd,
            },
            headers={"Content-Type": "application/json"},
            proxies=context.request_parameter.proxies,
            timeout=context.request_parameter.timeout,
            verify=context.request_parameter.verify,
        )
        token_response.raise_for_status()
        token = token_response.json().get("data", {}).get("token")
        if not token:
            raise ValueError("Got no session token.\n")

        sms_data = {
            "number": context.request_parameter.recipient,
            "message": context.message,
            "modem": "3-1",
        }

        sms_response = requests.post(
            context.request_parameter.url + "/api/messages/actions/send",
            json={"data": sms_data},
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            proxies=context.request_parameter.proxies,
            timeout=context.request_parameter.timeout,
            verify=context.request_parameter.verify,
        )
        sms_response.raise_for_status()

        if sms_response.json().get("success") is True and sms_response.status_code == 200:
            sys.stdout.write("Notification successfully sent via sms.\n")
            return 0

        return 2

    except ValueError as e:
        sys.stderr.write(f"Error calling API: {e}")
        return 2


def _trb140_mobile_post(context: Context) -> requests.Response:
    """This endpoint has to be used until firmware version 7.13"""
    return requests.post(
        context.request_parameter.url + "/cgi-bin/sms_send",
        proxies=context.request_parameter.proxies,
        timeout=context.request_parameter.timeout,
        data={
            "username": context.request_parameter.user,
            "password": context.request_parameter.pwd,
            "number": context.request_parameter.recipient,
            "text": context.message,
        },
        verify=context.request_parameter.verify,
    )


def main() -> NoReturn:
    """Construct needed context and call the related class."""
    raw_context: PluginNotificationContext = collect_context()

    context = _get_context_parameter(raw_context)

    if isinstance(context, Errors):
        sys.stdout.write(" ".join(context))
        sys.exit(2)

    sys.exit(context.send_function(context))


# .
