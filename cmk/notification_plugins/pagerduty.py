#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
r"""
Send notification messages to PagerDuty
=======================================

"""

from typing import Any

from cmk.notification_plugins.utils import (
    get_password_from_env_or_context,
    host_url_from_context,
    post_request,
    process_by_status_code,
    service_url_from_context,
)


def pagerduty_event_type(event: str) -> str:
    return {
        "PROBLEM": "trigger",
        "CUSTOM": "trigger",
        "ACKNOWLEDGEMENT": "acknowledge",
        "RECOVERY": "resolve",
        "FLAPPINGSTART": "trigger",
        "FLAPPINGSTOP": "resolve",
    }[event]


def pagerduty_severity(state: str) -> str:
    return {
        "CRITICAL": "critical",
        "DOWN": "critical",
        "WARNING": "warning",
        "OK": "info",
        "UP": "info",
        "UNKNOWN": "error",
        "UNREACHABLE": "error",
    }[state]


def _notification_source_from_context(context: dict[str, str]) -> str:
    """
    payload.source must not be empty, otherwise:
    HTTP 400 (Bad Request), "'payload.source' is missing or blank"
    """
    return context.get("HOSTADDRESS") or context.get("HOSTNAME") or "Undeclared Host identifier"


def _pagerduty_msg(context: dict[str, str]) -> dict[str, Any]:
    """Build the PagerDuty incident payload"""

    if context.get("WHAT") == "SERVICE":
        state = context["SERVICESTATE"]
        incident_key = "{SERVICEDESC}/{HOSTNAME}:{HOSTADDRESS}".format(**context).replace(" ", "")
        incident = "{SERVICESTATE}: {SERVICEDESC} on {HOSTNAME}".format(**context)
        output = context["SERVICEOUTPUT"]
        incident_url = service_url_from_context(context)
    else:
        state = context["HOSTSTATE"]
        incident_key = "{HOSTNAME}:{HOSTADDRESS}".format(**context).replace(" ", "")
        incident = "{HOSTNAME} is {HOSTSTATE}".format(**context)
        output = context["HOSTOUTPUT"]
        incident_url = host_url_from_context(context)

    msg_payload = {
        "routing_key": get_password_from_env_or_context(
            key="PARAMETER_ROUTING_KEY", context=context
        ),
        "event_action": pagerduty_event_type(context["NOTIFICATIONTYPE"]),
        "dedup_key": incident_key,
        "payload": {
            "summary": incident,
            "source": _notification_source_from_context(context),
            "severity": pagerduty_severity(state),
            "custom_details": {
                "info": output,
                "host": context.get("HOSTNAME"),
                "host_address": context.get("HOSTADDRESS"),
            },
        },
    }
    if incident_url:
        msg_payload.update({"client": "Check_MK", "client_url": incident_url})

    return msg_payload


def main() -> int:
    # PagerDuty replies with 202 because the request is further processed
    # by them. Thus their reply only includes field validation checks.
    return process_by_status_code(post_request(_pagerduty_msg), success_code=202)
