#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
r"""
Send notification messages to Slack
===================================

Use a slack webhook to send notification messages
"""
from cmk.notification_plugins.utils import (
    format_link,
    host_url_from_context,
    post_request,
    process_by_status_code,
    service_url_from_context,
)

COLORS = {
    "CRITICAL": "#EE0000",
    "DOWN": "#EE0000",
    "WARNING": "#FFDD00",
    "OK": "#00CC00",
    "UP": "#00CC00",
    "UNKNOWN": "#CCCCCC",
    "UNREACHABLE": "#CCCCCC",
}


def _slack_msg(context: dict) -> dict[str, object]:
    """Build the message for slack"""

    if context.get("WHAT", None) == "SERVICE":
        color = COLORS.get(context["SERVICESTATE"])
        title = "Service {NOTIFICATIONTYPE} notification".format(**context)
        text = "Host: {host_link} (IP: {HOSTADDRESS})\nService: {service_link}\nState: {SERVICESTATE}".format(
            host_link=format_link("<%s|%s>", host_url_from_context(context), context["HOSTNAME"]),
            service_link=format_link(
                "<%s|%s>", service_url_from_context(context), context["SERVICEDESC"]
            ),
            **context,
        )
        output = context["SERVICEOUTPUT"]
    else:
        color = COLORS.get(context["HOSTSTATE"])
        title = "Host {NOTIFICATIONTYPE} notification".format(**context)
        text = "Host: {host_link} (IP: {HOSTADDRESS})\nState: {HOSTSTATE}".format(
            host_link=format_link("<%s|%s>", host_url_from_context(context), context["HOSTNAME"]),
            **context,
        )
        output = context["HOSTOUTPUT"]

    assert color is not None

    return {
        "attachments": [
            {
                "color": color,
                "title": title,
                "text": text,
            },
            {
                "color": color,
                "title": "Additional Info",
                "text": output
                + "\nPlease take a look: "
                + ", ".join(map("@{}".format, context["CONTACTNAME"].split(","))),
                "footer": "Check_MK notification: {LONGDATETIME}".format(**context),
            },
        ]
    }


def main() -> int:
    return process_by_status_code(post_request(_slack_msg))
