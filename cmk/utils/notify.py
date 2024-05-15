#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import logging
import os
import subprocess
import time
import uuid
from collections.abc import Mapping
from logging import Logger
from pathlib import Path
from typing import Final, Literal, NewType, TypedDict

import livestatus

import cmk.utils.statename as statename
from cmk.utils import store
from cmk.utils.config_path import VersionedConfigPath
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostName
from cmk.utils.i18n import _
from cmk.utils.labels import CollectedHostLabels
from cmk.utils.notify_types import EnrichedEventContext
from cmk.utils.notify_types import NotificationContext as NotificationContext
from cmk.utils.paths import core_helper_config_dir
from cmk.utils.store import load_object_from_file, save_object_to_file

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
    context: EnrichedEventContext


class NotificationViaPlugin(TypedDict):
    plugin: str
    context: NotificationContext


def _state_for(exit_code: NotificationResultCode) -> str:
    return statename.service_state_name(exit_code, "UNKNOWN")


def find_wato_folder(context: NotificationContext) -> str:
    return next(
        (
            tag[6:].rstrip("/")
            for tag in context.get("HOSTTAGS", "").split()
            if tag.startswith("/wato/")
        ),
        "",
    )


def notification_message(plugin: NotificationPluginName, context: NotificationContext) -> str:
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
    if service := context.get("SERVICEDESC"):
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
    if service := context.get("SERVICEDESC"):
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
    data: NotificationForward | NotificationResult | NotificationViaPlugin,
) -> None:
    spool_dir.mkdir(parents=True, exist_ok=True)
    file_path = spool_dir / str(uuid.uuid4())
    logger_.info("Creating spoolfile: %s", file_path)
    store.save_object_to_file(file_path, data, pretty=True)


def log_to_history(message: str) -> None:
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


def write_notify_host_file(
    config_path: VersionedConfigPath,
    labels_per_host: Mapping[HostName, CollectedHostLabels],
) -> None:
    notify_labels_path: Path = _get_host_file_path(config_path)
    for host, labels in labels_per_host.items():
        host_path = notify_labels_path / host
        save_object_to_file(
            host_path,
            dataclasses.asdict(
                CollectedHostLabels(
                    host_labels=labels.host_labels,
                    service_labels={k: v for k, v in labels.service_labels.items() if v.values()},
                )
            ),
        )


def read_notify_host_file(
    host_name: HostName,
) -> CollectedHostLabels:
    host_file_path: Path = _get_host_file_path(host_name=host_name)
    return CollectedHostLabels(
        **load_object_from_file(
            path=host_file_path,
            default={"host_labels": {}, "service_labels": {}},
        )
    )


def _get_host_file_path(
    config_path: VersionedConfigPath | None = None,
    host_name: HostName | None = None,
) -> Path:
    root_path = Path(config_path) if config_path else core_helper_config_dir / Path("latest")
    if host_name:
        return root_path / "notify" / "labels" / host_name
    return root_path / "notify" / "labels"
