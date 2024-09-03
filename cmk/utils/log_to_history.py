#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Helper to write notification related updates to the monitoring history

We wan to inform users about the processing of notifications so that they
understand better which part of the system did what with a notification
initially created by the monitoring core.

This module provides a way to write the information to the monitoring history
by sending the message to the local monitoring core.
"""

import logging
import time
from typing import Final, NewType

import livestatus

from cmk.utils import statename
from cmk.utils.notification_result import (
    NotificationContext,
    NotificationPluginName,
    NotificationResultCode,
)

SanitizedLivestatusLogStr = NewType("SanitizedLivestatusLogStr", str)

# NOTE: Keep in sync with values in MonitoringLog.cc.
MAX_COMMENT_LENGTH = 2000
MAX_PLUGIN_OUTPUT_LENGTH = 1000
# from https://www.w3schools.com/tags/ref_urlencode.ASP
# Nagios uses ":", which is even more surprising, I guess.
_SEMICOLON: Final = "%3B"

logger = logging.getLogger(__name__)


def log_to_history(message: SanitizedLivestatusLogStr) -> None:
    _livestatus_cmd(f"LOG;{message}")


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


def notification_message(
    plugin: NotificationPluginName, context: NotificationContext
) -> SanitizedLivestatusLogStr:
    contact = context["CONTACTNAME"]
    hostname = context["HOSTNAME"]
    if service := context.get("SERVICEDESC"):
        what = "SERVICE NOTIFICATION"
        spec = f"{hostname};{service}"
        state = context["SERVICESTATE"]
        output = context["SERVICEOUTPUT"]
    else:
        what = "HOST NOTIFICATION"
        spec = hostname
        state = context["HOSTSTATE"]
        output = context["HOSTOUTPUT"]
    # NOTE: There are actually 3 more additional fields, which we don't use: author, comment and long plug-in output.
    return SanitizedLivestatusLogStr(
        "{}: {};{};{};{};{}".format(
            what,
            livestatus.lqencode(contact),
            livestatus.lqencode(spec),
            livestatus.lqencode(state),
            livestatus.lqencode(plugin),
            livestatus.lqencode(output[:MAX_PLUGIN_OUTPUT_LENGTH].replace(";", _SEMICOLON)),
        )
    )


def notification_progress_message(
    plugin: NotificationPluginName,
    contact: str,
    hostname: str,
    service: str | None,
    exit_code: NotificationResultCode,
    output: str,
) -> SanitizedLivestatusLogStr:
    if service:
        what = "SERVICE NOTIFICATION PROGRESS"
        spec = f"{hostname};{service}"
    else:
        what = "HOST NOTIFICATION PROGRESS"
        spec = hostname
    state = _state_for(exit_code)
    return SanitizedLivestatusLogStr(
        "{}: {};{};{};{};{}".format(
            what,
            livestatus.lqencode(contact),
            livestatus.lqencode(spec),
            state,
            livestatus.lqencode(plugin),
            livestatus.lqencode(output[:MAX_PLUGIN_OUTPUT_LENGTH].replace(";", _SEMICOLON)),
        )
    )


def notification_result_message(
    plugin: NotificationPluginName,
    contact: str,
    hostname: str,
    service: str | None,
    exit_code: NotificationResultCode,
    output: list[str],
) -> SanitizedLivestatusLogStr:
    if service:
        what = "SERVICE NOTIFICATION RESULT"
        spec = f"{hostname};{service}"
    else:
        what = "HOST NOTIFICATION RESULT"
        spec = hostname
    state = _state_for(exit_code)
    comment = " -- ".join(output)
    short_output = output[-1] if output else ""
    return SanitizedLivestatusLogStr(
        "{}: {};{};{};{};{};{}".format(
            what,
            livestatus.lqencode(contact),
            livestatus.lqencode(spec),
            state,
            livestatus.lqencode(plugin),
            livestatus.lqencode(short_output[:MAX_PLUGIN_OUTPUT_LENGTH].replace(";", _SEMICOLON)),
            livestatus.lqencode(comment[:MAX_COMMENT_LENGTH].replace(";", _SEMICOLON)),
        )
    )


def _state_for(exit_code: NotificationResultCode) -> str:
    return statename.service_state_name(exit_code, "UNKNOWN")
