#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
r"""
Send notification messages to Cisco Webex Teams
===============================================

Use a Cisco Webex Teams webhook to send notification messages
"""

from cmk.notification_plugins.utils import (
    format_link,
    host_url_from_context,
    post_request,
    process_by_status_code,
    service_url_from_context,
)


def _cisco_webex_teams_msg(context: dict) -> dict:
    """Build the message for Cisco Webex Teams. We use the Markdown markup language, see
    https://developer.webex.com/docs/api/basics. For example, we need two spaces before a newline
    character."""

    notification_type = "%s notification" % context["NOTIFICATIONTYPE"]

    # notification about a service
    if context.get("WHAT", None) == "SERVICE":
        monitored_type = "Service"
        host_service_info = "Host: {} (IP: {})  \nService: {}".format(
            format_link("[%s](%s)", context["HOSTNAME"], host_url_from_context(context)),
            context["HOSTADDRESS"],
            format_link("[%s](%s)", context["SERVICEDESC"], service_url_from_context(context)),
        )
        state = "State: %s" % context["SERVICESTATE"]
        output = context["SERVICEOUTPUT"]

    # notification about a host
    else:
        monitored_type = "Host"
        host_service_info = "Host: {} (IP: {})".format(
            format_link("[%s](%s)", context["HOSTNAME"], host_url_from_context(context)),
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


def main() -> int:
    return process_by_status_code(
        response=post_request(_cisco_webex_teams_msg),
        success_code=204,
    )
