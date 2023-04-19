#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import subprocess
import time
import uuid
from logging import Logger
from pathlib import Path
from typing import Final, Literal, NewType, TypedDict

import livestatus

import cmk.utils.defines
from cmk.utils import store
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.i18n import _
from cmk.utils.type_defs import EventContext, NotificationContext

logger = logging.getLogger("cmk.utils.notify")

# NOTE: Keep in sync with values in MonitoringLog.cc.
MAX_COMMENT_LENGTH = 2000
MAX_PLUGIN_OUTPUT_LENGTH = 1000
_SEMICOLON: Final = "%3B"
# from https://www.w3schools.com/tags/ref_urlencode.ASP
# Nagios uses ":", which is even more surprising, I guess.

# 0 -> OK
# 1 -> temporary issue
# 2 -> permanent issue
NotificationResultCode = NewType("NotificationResultCode", int)
NotificationPluginName = NewType("NotificationPluginName", str)


class NotificationResult(TypedDict, total=False):
    plugin: NotificationPluginName
    status: NotificationResultCode
    output: list[str]
    forward: bool
    context: NotificationContext


class NotificationForward(TypedDict):
    forward: Literal[True]
    context: EventContext


class NotificationViaPlugin(TypedDict):
    plugin: str
    context: NotificationContext


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
        spec = f"{hostname};{service}"
        state = context["SERVICESTATE"]
        output = context["SERVICEOUTPUT"]
    else:
        what = "HOST NOTIFICATION"
        spec = hostname
        state = context["HOSTSTATE"]
        output = context["HOSTOUTPUT"]
    # NOTE: There are actually 3 more additional fields, which we don't use: author, comment and long plugin output.
    return "{}: {};{};{};{};{}".format(
        what,
        contact,
        spec,
        state,
        plugin,
        output[:MAX_PLUGIN_OUTPUT_LENGTH].replace(";", _SEMICOLON),
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
        spec = f"{hostname};{service}"
    else:
        what = "HOST NOTIFICATION PROGRESS"
        spec = hostname
    state = _state_for(exit_code)
    return "{}: {};{};{};{};{}".format(
        what,
        contact,
        spec,
        state,
        plugin,
        output[:MAX_PLUGIN_OUTPUT_LENGTH].replace(";", _SEMICOLON),
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
        spec = f"{hostname};{service}"
    else:
        what = "HOST NOTIFICATION RESULT"
        spec = hostname
    state = _state_for(exit_code)
    comment = " -- ".join(output)
    short_output = output[-1] if output else ""
    return "{}: {};{};{};{};{};{}".format(
        what,
        contact,
        spec,
        state,
        plugin,
        short_output[:MAX_PLUGIN_OUTPUT_LENGTH].replace(";", _SEMICOLON),
        comment[:MAX_COMMENT_LENGTH].replace(";", _SEMICOLON),
    )


def ensure_utf8(logger_: Logger | None = None) -> None:
    # Make sure that mail(x) is using UTF-8. Otherwise we cannot send notifications
    # with non-ASCII characters. Unfortunately we do not know whether C.UTF-8 is
    # available. If e.g. mail detects a non-Ascii character in the mail body and
    # the specified encoding is not available, it will silently not send the mail!
    # Our resultion in future: use /usr/sbin/sendmail directly.
    # Our resultion in the present: look with locale -a for an existing UTF encoding
    # and use that.
    with subprocess.Popen(
        ["locale", "-a"],
        close_fds=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    ) as proc:
        std_out = proc.communicate()[0]
        exit_code = proc.returncode
        error_msg = _("Command 'locale -a' could not be executed. Exit code of command was")
        not_found_msg = _(
            "No UTF-8 encoding found in your locale -a! Please install appropriate locales."
        )
        if exit_code != 0:
            if not logger_:
                raise MKGeneralException(f"{error_msg}: {exit_code!r}. {not_found_msg}")
            logger_.info(f"{error_msg}: {exit_code!r}")
            logger_.info(not_found_msg)
            return

        locales_list = std_out.decode("utf-8", "ignore").split("\n")
        for encoding in locales_list:
            el: str = encoding.lower()
            if "utf8" in el or "utf-8" in el or "utf.8" in el:
                encoding = encoding.strip()
                os.putenv("LANG", encoding)
                if logger_:
                    logger_.debug("Setting locale for mail to %s.", encoding)
                break
        else:
            if not logger_:
                raise MKGeneralException(not_found_msg)
            logger_.info(not_found_msg)


def create_spoolfile(
    logger_: Logger,
    spool_dir: Path,
    data: (NotificationForward | NotificationResult | NotificationViaPlugin),
) -> None:
    spool_dir.mkdir(parents=True, exist_ok=True)
    file_path = spool_dir / str(uuid.uuid4())
    logger_.info("Creating spoolfile: %s", file_path)
    store.save_object_to_file(file_path, data, pretty=True)


def log_to_history(message: str) -> None:
    _livestatus_cmd("LOG;%s" % message)


def _livestatus_cmd(command: str) -> None:
    logger.info("sending command %s", command)
    timeout = 2
    try:
        connection = livestatus.LocalConnection()
        connection.set_timeout(timeout)
        connection.command("[%d] %s" % (time.time(), command))
    except Exception:
        logger.exception("Cannot send livestatus command (Timeout: %d sec)", timeout)
        logger.info("Command was: %s", command)


def transform_flexible_and_plain_context(context: NotificationContext) -> NotificationContext:
    if "CONTACTS" not in context:
        context["CONTACTS"] = context.get("CONTACTNAME", "?")
        context["PARAMETER_GRAPHS_PER_NOTIFICATION"] = "5"
        context["PARAMETER_NOTIFICATIONS_WITH_GRAPHS"] = "5"
    return context


def transform_flexible_and_plain_plugin(
    plugin: NotificationPluginName | None,
) -> NotificationPluginName:
    return plugin or NotificationPluginName("mail")
