#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NewType

import cmk.utils.defines

# NOTE: Keep in sync with values in MonitoringLog.cc.
MAX_COMMENT_LENGTH = 2000
MAX_PLUGIN_OUTPUT_LENGTH = 1000

# 0 -> OK
# 1 -> temporary issue
# 2 -> permanent issue
NotificationResultCode = NewType("NotificationResultCode", int)
NotificationPluginName = NewType("NotificationPluginName", str)
NotificationContext = NewType("NotificationContext", dict[str, str])


def _state_for(exit_code: NotificationResultCode) -> str:
    return cmk.utils.defines.service_state_name(exit_code, "UNKNOWN")


def find_wato_folder(context: NotificationContext) -> str:
    for tag in context.get("HOSTTAGS", "").split():
        if tag.startswith("/wato/"):
            return tag[6:].rstrip("/")
    return ""


def notification_message(plugin: NotificationPluginName, context: NotificationContext) -> str:
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
    # NOTE: There are actually 3 more additional fields, which we don't use: author, comment and long plugin output.
    return "%s: %s;%s;%s;%s;%s" % (
        what,
        contact,
        spec,
        state,
        plugin,
        output[:MAX_PLUGIN_OUTPUT_LENGTH],
    )


def notification_progress_message(
    plugin: NotificationPluginName,
    context: NotificationContext,
    exit_code: NotificationResultCode,
    output: str,
) -> str:
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
    return "%s: %s;%s;%s;%s;%s" % (
        what,
        contact,
        spec,
        state,
        plugin,
        output[:MAX_PLUGIN_OUTPUT_LENGTH],
    )


def notification_result_message(
    plugin: NotificationPluginName,
    context: NotificationContext,
    exit_code: NotificationResultCode,
    output: list[str],
) -> str:
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
    return "%s: %s;%s;%s;%s;%s;%s" % (
        what,
        contact,
        spec,
        state,
        plugin,
        short_output[:MAX_PLUGIN_OUTPUT_LENGTH],
        comment[:MAX_COMMENT_LENGTH],
    )
