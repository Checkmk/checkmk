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
Send notification messages to VictorOPS
=======================================

Create a JSON message to be sent to VictorOPS REST API
"""
from __future__ import unicode_literals

from typing import Dict  # pylint: disable=unused-import

from cmk.notification_plugins.utils import host_url_from_context, service_url_from_context


def translate_states(state):
    if state in ['OK', 'UP']:
        return 'OK'
    if state in ['CRITICAL', 'DOWN']:
        return 'CRITICAL'
    if state in ['UNKNOWN', 'UNREACHABLE']:
        return 'INFO'
    return state  # This is WARNING


def victorops_msg(context):
    # type: (Dict) -> Dict
    """Build the message for slack"""

    if context.get('WHAT', None) == "SERVICE":
        state = translate_states(context["SERVICESTATE"])
        entity_id = '{SERVICEDESC}/{HOSTNAME}:{HOSTADDRESS}'.format(**context).replace(" ", "")
        title = "{SERVICEDESC} on {HOSTNAME}".format(**context)
        text = "{SERVICEOUTPUT}\n\n{service_url}".format(
            service_url=service_url_from_context(context), **context)
    else:
        state = translate_states(context["HOSTSTATE"])
        entity_id = '{HOSTNAME}:{HOSTADDRESS}'.format(**context).replace(" ", "")
        title = '{HOSTNAME} is {HOSTSTATE}'.format(**context)
        text = "{HOSTOUTPUT}\n\n{host_url}".format(host_url=host_url_from_context(context),
                                                   **context)
    hostname = context.get('HOSTNAME')

    return {
        "message_type": state,
        "entity_id": entity_id,
        "entity_display_name": title,
        "state_message": text,
        "host_name": hostname,
        "monitoring_tool": "Check_MK notification",
    }
