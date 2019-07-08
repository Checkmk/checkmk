# -*- coding: utf-8 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2018             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
r"""
Send notification messages to Slack
===================================

Use a slack webhook to send notification messages
"""
from __future__ import unicode_literals

from typing import Dict  # pylint: disable=unused-import

from cmk.notification_plugins.utils import extend_context_with_link_urls

COLORS = {
    "CRITICAL": "#EE0000",
    "DOWN": "#EE0000",
    "WARNING": "#FFDD00",
    "OK": "#00CC00",
    "UP": "#00CC00",
    "UNKNOWN": "#CCCCCC",
    "UNREACHABLE": "#CCCCCC",
}


def slack_msg(context):
    # type: (Dict) -> Dict
    """Build the message for slack"""

    extend_context_with_link_urls(context, '<{}|{}>')

    if context.get('WHAT', None) == "SERVICE":
        color = COLORS.get(context["SERVICESTATE"])
        title = "Service {NOTIFICATIONTYPE} notification".format(**context)
        text = "Host: {LINKEDHOSTNAME} (IP: {HOSTADDRESS})\nService: {LINKEDSERVICEDESC}\nState: {SERVICESTATE}".format(
            **context)
        output = context["SERVICEOUTPUT"]
    else:
        color = COLORS.get(context["HOSTSTATE"])
        title = "Host {NOTIFICATIONTYPE} notification".format(**context)
        text = "Host: {LINKEDHOSTNAME} (IP: {HOSTADDRESS})\nState: {HOSTSTATE}".format(**context)
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
                "text": output + "\nPlease take a look: " +
                        ", ".join(map("@{}".format, context["CONTACTNAME"].split(','))),
                "footer": "Check_MK notification: {LONGDATETIME}".format(**context),
            },
        ]
    }
