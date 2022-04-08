#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import subprocess
from logging import Logger
from typing import Dict, List, NewType, Optional

import cmk.utils.defines
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.i18n import _

# NOTE: Keep in sync with values in Object.h.
MAX_COMMENT_LENGTH = 2000
MAX_PLUGIN_OUTPUT_LENGTH = 1000

# 0 -> OK
# 1 -> temporary issue
# 2 -> permanent issue
NotificationResultCode = NewType("NotificationResultCode", int)
NotificationPluginName = NewType("NotificationPluginName", str)
NotificationContext = NewType("NotificationContext", Dict)


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


def notification_progress_message(plugin: NotificationPluginName, context: NotificationContext,
                                  exit_code: NotificationResultCode, output: str) -> str:
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


def notification_result_message(plugin: NotificationPluginName, context: NotificationContext,
                                exit_code: NotificationResultCode, output: List[str]) -> str:
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


def ensure_utf8(logger: Optional[Logger] = None) -> None:
    # Make sure that mail(x) is using UTF-8. Otherwise we cannot send notifications
    # with non-ASCII characters. Unfortunately we do not know whether C.UTF-8 is
    # available. If e.g. mail detects a non-Ascii character in the mail body and
    # the specified encoding is not available, it will silently not send the mail!
    # Our resultion in future: use /usr/sbin/sendmail directly.
    # Our resultion in the present: look with locale -a for an existing UTF encoding
    # and use that.
    proc: subprocess.Popen = subprocess.Popen(
        ["locale", "-a"],
        close_fds=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    locales_list: List[str] = []
    std_out: bytes = proc.communicate()[0]
    exit_code: int = proc.returncode
    error_msg: str = _("Command 'locale -a' could not be executed. Exit code of command was")
    not_found_msg: str = _("No UTF-8 encoding found in your locale -a! "\
                         "Please install appropriate locales.")
    if exit_code != 0:
        if not logger:
            raise MKGeneralException("%s: %r. %s" % (error_msg, exit_code, not_found_msg))
        logger.info("%s: %r" % (error_msg, exit_code))
        logger.info(not_found_msg)
        return

    locales_list = std_out.decode('utf-8', 'ignore').split("\n")
    for encoding in locales_list:
        el: str = encoding.lower()
        if "utf8" in el or "utf-8" in el or "utf.8" in el:
            encoding = encoding.strip()
            os.putenv("LANG", encoding)
            if logger:
                logger.debug("Setting locale for mail to %s.", encoding)
            break
    else:
        if not logger:
            raise MKGeneralException(not_found_msg)
        logger.info(not_found_msg)

    return
