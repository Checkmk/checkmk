#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

import cmk.utils.defines


def _state_for(exit_code):
    # The exit codes are not really service states, but we treat them like this.
    # 0 -> OK
    # 1 -> temporary issue
    # 2 -> permanent issue
    return cmk.utils.defines.service_state_name(exit_code, "UNKNOWN")


def find_wato_folder(context):
    for tag in context.get("HOSTTAGS", "").split():
        if tag.startswith("/wato/"):
            return tag[6:].rstrip("/")
    return ""


def notification_message(plugin, context):
    contact = context["CONTACTNAME"]
    hostname = context["HOSTNAME"]
    service = context.get("SERVICEDESC")
    if service:
        what = "SERVICE NOTIFICATION"
        spec = "%s;%s" % (hostname, service)
        state = context["SERVICESTATE"]
        output = context["SERVICEOUTPUT"]
    else:
        what = "HOST NOTIFICATION"
        spec = hostname
        state = context["HOSTSTATE"]
        output = context["HOSTOUTPUT"]
    return "%s: %s;%s;%s;%s;%s" % (what, contact, spec, state, plugin, output)


def notification_progress_message(plugin, context, exit_code, output):
    contact = context["CONTACTNAME"]
    hostname = context["HOSTNAME"]
    service = context.get("SERVICEDESC")
    if service:
        what = "SERVICE NOTIFICATION PROGRESS"
        spec = "%s;%s" % (hostname, service)
    else:
        what = "HOST NOTIFICATION PROGRESS"
        spec = hostname
    state = _state_for(exit_code)
    return "%s: %s;%s;%s;%s;%s" % (what, contact, spec, state, plugin, output)


def notification_result_message(plugin, context, exit_code, output):
    contact = context["CONTACTNAME"]
    hostname = context["HOSTNAME"]
    service = context.get("SERVICEDESC")
    if service:
        what = "SERVICE NOTIFICATION RESULT"
        spec = "%s;%s" % (hostname, service)
    else:
        what = "HOST NOTIFICATION RESULT"
        spec = hostname
    state = _state_for(exit_code)
    comment = " -- ".join(output)
    output = output[-1]
    return "%s: %s;%s;%s;%s;%s;%s" % (what, contact, spec, state, plugin, output, comment)
