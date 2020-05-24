#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
r"""
Send notification messages to Discord
===================================

Use a discord webhook to send notification messages
"""
from typing import Dict

import six

import cmk.notification_plugins.utils as utils

COLORS = {
    "CRITICAL": 15597568,
    "DOWN": 15597568,
    "WARNING": 16768256,
    "OK": 52224,
    "UP": 52224,
    "UNKNOWN": 13421772,
    "UNREACHABLE": 13421772,
}


def discord_msg(context):
    # type: (Dict) -> Dict
    """Build the message for discord"""

    if context.get('WHAT', None) == "SERVICE":
        color = COLORS.get(context["SERVICESTATE"])
        title = "Service {NOTIFICATIONTYPE} notification".format(**context)
        text = "Host: {host_link} (IP: {HOSTADDRESS})\nService: {service_link}\nState: {SERVICESTATE}".format(
            host_link=utils.format_link(six.ensure_str('<%s|%s>'),
                                        utils.host_url_from_context(context), context['HOSTNAME']),
            service_link=utils.format_link(six.ensure_str('<%s|%s>'),
                                           utils.service_url_from_context(context),
                                           context['SERVICEDESC']),
            **context)
        output = context["SERVICEOUTPUT"]
    else:
        color = COLORS.get(context["HOSTSTATE"])
        title = "Host {NOTIFICATIONTYPE} notification".format(**context)
        text = "Host: {host_link} (IP: {HOSTADDRESS})\nState: {HOSTSTATE}".format(
            host_link=utils.format_link(six.ensure_str('<%s|%s>'),
                                        utils.host_url_from_context(context), context['HOSTNAME']),
            **context)
        output = context["HOSTOUTPUT"]

    return {
        "username": "checkmk",
        "avatar_url": "https://checkmk.com/images/apple-touch-icon.png",
        "content": output + "\nPlease take a look: " +
                ", ".join(map("@{}".format, context["CONTACTNAME"].split(','))),
        "embeds": [
            {
                "color": color,
                "title": title,
                "description": text,
                "footer": {
                    "text:": "Check_MK notification: {LONGDATETIME}".format(**context)
                }
            }
        ]
    }
