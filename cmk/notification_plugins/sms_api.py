#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from dataclasses import dataclass
from typing import NoReturn, Optional, Union

import requests

from cmk.notification_plugins.utils import (  # pylint: disable=cmk-module-layer-violation
    collect_context,
    get_sms_message_from_context,
    quote_message,
    retrieve_from_passwordstore,
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
RawContext = dict[str, str]


@dataclass
class RequestParameter:
    """Dataclass for request related context parameter for all modems."""

    recipient: str
    url: str
    verify: bool
    proxies: Optional[dict[str, str]]
    user: str
    pwd: str
    timeout: float


@dataclass
class Context:
    url: str
    request_parameter: RequestParameter
    message: Message
    data: dict[str, str]


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
def _get_context_parameter(raw_context: RawContext) -> Union[Errors, Context]:
    """First, get the request parameters for sendind the sms. Then construct
    the sms message and get the endpoint specific parameters to return the
    context for notification processing.
    """
    missing_params: list[str] = []
    for mandatory in [
        "PARAMETER_MODEM_TYPE",
        "PARAMETER_URL",
        "PARAMETER_USERNAME",
        "PARAMETER_PASSWORD",
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
            url=request_parameter.url + "/cgi-bin/sms_send",
            request_parameter=request_parameter,
            message=message,
            data={
                "username": request_parameter.user,
                "password": request_parameter.pwd,
                "number": request_parameter.recipient,
                "text": message,
            },
        )

    return Errors(["Unknown unsupported modem: %s" % endpoint])


def _get_request_params_from_context(raw_context: RawContext) -> Union[Errors, RequestParameter]:
    recipient = raw_context["CONTACTPAGER"].replace(" ", "")
    if not recipient:
        return Errors(["Error: Pager Number of %s not set\n" % raw_context["CONTACTNAME"]])

    proxy_url = raw_context.get("PARAMETER_PROXY_URL", "")
    proxies = {"https": proxy_url} if proxy_url else None

    return RequestParameter(
        recipient=recipient,
        url=raw_context["PARAMETER_URL"],
        verify="PARAMETER_IGNORE_SSL" in raw_context,
        proxies=proxies,
        user=raw_context["PARAMETER_USERNAME"],
        pwd=retrieve_from_passwordstore(raw_context["PARAMETER_PASSWORD"]),
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


def process_notifications(context: Context) -> int:
    """Main processing of notifications for this API endpoint."""
    response = requests.post(
        context.url,
        proxies=context.request_parameter.proxies,
        timeout=context.request_parameter.timeout,
        data=context.data,
        verify=context.request_parameter.verify,
    )

    if response.status_code != 200 or response.content != b"OK\n":
        sys.stderr.write(
            "Error Status: %s Details: %r\n" % (response.status_code, response.content)
        )
        return 2

    sys.stdout.write("Notification successfully send via sms.\n")

    return 0


def main() -> NoReturn:
    """Construct needed context and call the related class."""
    raw_context: RawContext = collect_context()

    context = _get_context_parameter(raw_context)

    if isinstance(context, Errors):
        sys.stdout.write(" ".join(context))
        sys.exit(2)

    sys.exit(process_notifications(context))


# .
