#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
r"""
Send notification messages to Cisco Webex Teams
===============================================

Use a Cisco Webex Teams webhook to send notification messages
"""
from typing import Dict

import cmk.notification_plugins.utils as utils


def cisco_webex_teams_msg(context: Dict) -> Dict:
    """Build the message for Cisco Webex Teams. We use the Markdown markup language, see
    https://developer.webex.com/docs/api/basics. For example, we need two spaces before a newline
    character."""

    notification_type = "%s notification" % context["NOTIFICATIONTYPE"]

    # notification about a service
    if context.get("WHAT", None) == "SERVICE":
        monitored_type = "Service"
        host_service_info = "Host: %s (IP: %s)  \nService: %s" % (
            utils.format_link("<%s|%s>", utils.host_url_from_context(context), context["HOSTNAME"]),
            context["HOSTADDRESS"],
            utils.format_link(
                "<%s|%s>", utils.service_url_from_context(context), context["SERVICEDESC"]
            ),
        )
        state = "State: %s" % context["SERVICESTATE"]
        output = context["SERVICEOUTPUT"]

    # notification about a host
    else:
        monitored_type = "Host"
        host_service_info = "Host: %s (IP: %s)" % (
            utils.format_link("<%s|%s>", utils.host_url_from_context(context), context["HOSTNAME"]),
            context["HOSTADDRESS"],
        )
        state = "State: %s" % context["HOSTSTATE"]
        output = context["HOSTOUTPUT"]

    markdown = (
        "#### "
        + monitored_type
        + " "
        + notification_type
        + "  \n"
        + host_service_info
        + "  \n"
        + state
        + "  \n#### Additional Info"
        + "  \n"
        + output
        + "  \nPlease take a look: "
        + ", ".join(["@" + contact_name for contact_name in context["CONTACTNAME"].split(",")])
        + "  \nCheck_MK notification: %s" % context["LONGDATETIME"]
    )

    return {"markdown": markdown}
