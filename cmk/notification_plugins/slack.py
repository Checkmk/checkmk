#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
r"""
Send notification messages to Slack
===================================

Use a slack webhook to send notification messages
"""
from typing import Dict

import cmk.notification_plugins.utils as utils

COLORS = {
    "CRITICAL": "#EE0000",
    "DOWN": "#EE0000",
    "WARNING": "#FFDD00",
    "OK": "#00CC00",
    "UP": "#00CC00",
    "UNKNOWN": "#CCCCCC",
    "UNREACHABLE": "#CCCCCC",
}


def slack_msg(context: Dict) -> Dict:
    """Build the message for slack"""

    if context.get("WHAT", None) == "SERVICE":
        color = COLORS.get(context["SERVICESTATE"])
        title = "Service {NOTIFICATIONTYPE} notification".format(**context)
        text = "Host: {host_link} (IP: {HOSTADDRESS})\nService: {service_link}\nState: {SERVICESTATE}".format(
            host_link=utils.format_link(
                "<%s|%s>", utils.host_url_from_context(context), context["HOSTNAME"]
            ),
            service_link=utils.format_link(
                "<%s|%s>", utils.service_url_from_context(context), context["SERVICEDESC"]
            ),
            **context,
        )
        output = context["SERVICEOUTPUT"]
    else:
        color = COLORS.get(context["HOSTSTATE"])
        title = "Host {NOTIFICATIONTYPE} notification".format(**context)
        text = "Host: {host_link} (IP: {HOSTADDRESS})\nState: {HOSTSTATE}".format(
            host_link=utils.format_link(
                "<%s|%s>", utils.host_url_from_context(context), context["HOSTNAME"]
            ),
            **context,
        )
        output = context["HOSTOUTPUT"]

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
