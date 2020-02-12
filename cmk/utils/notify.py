#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NewType, Text, Dict, List  # pylint: disable=unused-import

import cmk.utils.defines

# 0 -> OK
# 1 -> temporary issue
# 2 -> permanent issue
NotificationResultCode = NewType("NotificationResultCode", int)
NotificationPluginName = NewType("NotificationPluginName", Text)
NotificationContext = NewType("NotificationContext", Dict)


def _state_for(exit_code):
    # type: (NotificationResultCode) -> Text
    return cmk.utils.defines.service_state_name(exit_code, u"UNKNOWN")


def find_wato_folder(context):
    # type: (NotificationContext) -> Text
    for tag in context.get("HOSTTAGS", "").split():
        if tag.startswith("/wato/"):
            return tag[6:].rstrip("/")
    return u""


def notification_message(plugin, context):
    # type: (NotificationPluginName, NotificationContext) -> Text
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
    return u"%s: %s;%s;%s;%s;%s" % (what, contact, spec, state, plugin, output)


def notification_progress_message(plugin, context, exit_code, output):
    # type: (NotificationPluginName, NotificationContext, NotificationResultCode, Text) -> Text
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
    return u"%s: %s;%s;%s;%s;%s" % (what, contact, spec, state, plugin, output)


def notification_result_message(plugin, context, exit_code, output):
    # type: (NotificationPluginName, NotificationContext, NotificationResultCode, List[Text]) -> Text
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
    short_output = output[-1] if output else ""
    return u"%s: %s;%s;%s;%s;%s;%s" % (what, contact, spec, state, plugin, short_output, comment)
