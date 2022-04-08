#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
r"""
Send notification messages to Splunk On-Call
=======================================

Create a JSON message to be sent to Splunk On-Call REST API
"""

from cmk.notification_plugins.utils import host_url_from_context, service_url_from_context


def translate_states(state: str) -> str:
    if state in ["OK", "UP"]:
        return "RECOVERY"
    if state in ["CRITICAL", "DOWN"]:
        return "CRITICAL"
    if state in ["UNKNOWN", "UNREACHABLE"]:
        return "INFO"
    return state  # This is WARNING


def victorops_msg(context: dict[str, str]) -> dict[str, str]:
    """Build the message for VictorOps"""

    if context.get("WHAT") == "SERVICE":
        state = translate_states(context["SERVICESTATE"])
        entity_id = "{SERVICEDESC}/{HOSTNAME}:{HOSTADDRESS}".format(**context).replace(" ", "")
        title = "{SERVICEDESC} on {HOSTNAME}".format(**context)
        text = "{SERVICEOUTPUT}\n\n{service_url}".format(
            service_url=service_url_from_context(context), **context
        )
    else:
        state = translate_states(context["HOSTSTATE"])
        entity_id = "{HOSTNAME}:{HOSTADDRESS}".format(**context).replace(" ", "")
        title = "{HOSTNAME} is {HOSTSTATE}".format(**context)
        text = "{HOSTOUTPUT}\n\n{host_url}".format(
            host_url=host_url_from_context(context), **context
        )
    hostname = context["HOSTNAME"]

    return {
        "message_type": state,
        "entity_id": entity_id,
        "entity_display_name": title,
        "state_message": text,
        "host_name": hostname,
        "monitoring_tool": "Check_MK notification",
    }
