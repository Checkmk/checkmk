#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
r"""
Send notification messages to Flowtriq
=======================================

Post alerts to a Flowtriq webhook endpoint for DDoS detection
and traffic analytics.
"""

from cmk.notification_plugins.utils import (
    get_password_from_env_or_context,
    host_url_from_context,
    post_request,
    process_by_status_code,
    service_url_from_context,
)


def _flowtriq_msg(context: dict[str, str]) -> dict[str, object]:
    """Build the message payload for Flowtriq"""

    if context.get("WHAT") == "SERVICE":
        state = context["SERVICESTATE"]
        service = context["SERVICEDESC"]
        output = context["SERVICEOUTPUT"]
        url = service_url_from_context(context)
    else:
        state = context["HOSTSTATE"]
        service = ""
        output = context["HOSTOUTPUT"]
        url = host_url_from_context(context)

    msg: dict[str, object] = {
        "source": "checkmk",
        "host": context["HOSTNAME"],
        "host_address": context.get("HOSTADDRESS", ""),
        "service": service,
        "state": state,
        "output": output,
        "notification_type": context["NOTIFICATIONTYPE"],
    }

    if url:
        msg["url"] = url

    return msg


def _get_headers() -> dict[str, str]:
    """Build request headers, including optional API key"""
    headers: dict[str, str] = {
        "Content-type": "application/json",
    }

    try:
        api_key = get_password_from_env_or_context(key="NOTIFY_PARAMETER_API_KEY")
        headers["X-API-Key"] = api_key
    except (KeyError, IndexError):
        pass

    return headers


def main() -> int:
    return process_by_status_code(
        post_request(_flowtriq_msg, headers=_get_headers()),
        success_code=(200, 201, 202),
    )
