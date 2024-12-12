#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Helper to write notification related updates to the monitoring history

We want to inform users about the processing of notifications so that they
understand better which part of the system did what with a notification
initially created by the monitoring core.

This module provides a way to write the information to the monitoring history
by sending the message to the local monitoring core.
"""

import logging
import time
from typing import Final, NewType

import livestatus

from .notification_result import (
    NOTIFICATION_RESULT_OK,
    NOTIFICATION_RESULT_PERMANENT_ISSUE,
    NOTIFICATION_RESULT_TEMPORARY_ISSUE,
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
        connection.command(f"[{time.time():.0f}] {command}")
    except livestatus.MKLivestatusException:
        logger.exception("Cannot send livestatus command (Timeout: %d sec)", timeout)
        logger.info("Command was: %s", command)


def _format_notification_message(
    plugin: NotificationPluginName,
    context: NotificationContext,
    type_suffix: str | None = None,
    exit_code: NotificationResultCode | None = None,
    output: str | list[str] | None = None,
) -> SanitizedLivestatusLogStr:
    """
    Format a notification message for the monitoring history.

    Args:
        plugin: Name of the notification plugin
        context: Context with at least the keys "CONTACTNAME" and "HOSTNAME"
        type_suffix: Optional suffix to append to the message type
        exit_code: Optional exit code of the notification,
                   will be used instead of "SERVICESTATE" or "HOSTSTATE"
        output: Optional output override of the notification,
                will be used instead of "SERVICEOUTPUT" or "HOSTOUTPUT".
                If a list is given, the last entry will be used as the output.
                If the first entry is empty, the output will be empty.
                The entire list will also be joined with " -- " and used as a comment.
    """
    contact = context["CONTACTNAME"]
    hostname = context["HOSTNAME"]
    state = _notification_result_code_to_state_name(exit_code) if exit_code is not None else None
    if isinstance(output, list):
        output_str: str = output[-1] if output else ""
        comment: str | None = " -- ".join(output)
    else:
        output_str = output or ""
        comment = None
    if service := context.get("SERVICEDESC"):
        what = "SERVICE NOTIFICATION"
        spec = f"{hostname};{service}"
        state = state or context.get("SERVICESTATE", "UNKNOWN")
        output_str = output_str or context.get("SERVICEOUTPUT", "")
    else:
        what = "HOST NOTIFICATION"
        spec = hostname
        state = state or context.get("HOSTSTATE", "UNKNOWN")
        output_str = output_str or context.get("HOSTOUTPUT", "")
    if type_suffix:
        what += f" {type_suffix}"
    # NOTE: There are actually 2 more additional fields, which we don't use:
    # author and long plug-in output.
    fields = ";".join(
        (
            livestatus.lqencode(contact),
            livestatus.lqencode(spec),
            livestatus.lqencode(state),
            livestatus.lqencode(plugin),
            livestatus.lqencode(output_str[:MAX_PLUGIN_OUTPUT_LENGTH].replace(";", _SEMICOLON)),
        )
    )
    if comment is not None:
        fields += f";{livestatus.lqencode(comment[:MAX_COMMENT_LENGTH].replace(";", _SEMICOLON))}"
    return SanitizedLivestatusLogStr(f"{what}: {fields}")


def notification_message(
    plugin: NotificationPluginName,
    context: NotificationContext,
) -> SanitizedLivestatusLogStr:
    """
    >>> notification_message(NotificationPluginName("hurz"), NotificationContext({"CONTACTNAME": "foo", "HOSTNAME": "bar"}))
    'HOST NOTIFICATION: foo;bar;UNKNOWN;hurz;'
    """
    return _format_notification_message(plugin, context)


def notification_progress_message(
    plugin: NotificationPluginName,
    context: NotificationContext,
    exit_code: NotificationResultCode,
    output: str,
) -> SanitizedLivestatusLogStr:
    return _format_notification_message(plugin, context, "PROGRESS", exit_code, output)


def notification_result_message(
    plugin: NotificationPluginName,
    context: NotificationContext,
    exit_code: NotificationResultCode,
    output: list[str],
) -> SanitizedLivestatusLogStr:
    return _format_notification_message(plugin, context, "RESULT", exit_code, output)


def _notification_result_code_to_state_name(exit_code: NotificationResultCode) -> str:
    """Map the notification result codes to service state names"""
    return {
        NOTIFICATION_RESULT_OK: "OK",
        NOTIFICATION_RESULT_TEMPORARY_ISSUE: "WARNING",
        NOTIFICATION_RESULT_PERMANENT_ISSUE: "CRITICAL",
    }.get(exit_code, "UNKNOWN")
