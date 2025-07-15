#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import logging
import os
import subprocess
from collections.abc import Mapping
from logging import Logger
from pathlib import Path

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.i18n import _
from cmk.ccc.store import load_object_from_file, save_object_to_file

from cmk.utils.config_path import VersionedConfigPath
from cmk.utils.labels import Labels
from cmk.utils.notify_types import NotificationContext as NotificationContext
from cmk.utils.servicename import ServiceName
from cmk.utils.tags import TagGroupID, TagID

logger = logging.getLogger("cmk.utils.notify")


@dataclasses.dataclass(frozen=True)
class NotificationHostConfig:
    host_labels: Labels
    service_labels: Mapping[ServiceName, Labels]
    tags: Mapping[TagGroupID, TagID]


def find_wato_folder(context: NotificationContext) -> str:
    return next(
        (
            tag[6:].rstrip("/")
            for tag in context.get("HOSTTAGS", "").split()
            if tag.startswith("/wato/")
        ),
        "",
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


def write_notify_host_file(
    config_path: Path,
    config_per_host: Mapping[HostName, NotificationHostConfig],
) -> None:
    notify_config_path: Path = _get_host_file_path(config_path)
    for host, labels in config_per_host.items():
        host_path = notify_config_path / host
        save_object_to_file(
            host_path,
            dataclasses.asdict(
                NotificationHostConfig(
                    host_labels=labels.host_labels,
                    service_labels={k: v for k, v in labels.service_labels.items() if v.values()},
                    tags=labels.tags,
                )
            ),
        )


def read_notify_host_file(
    host_name: HostName,
) -> NotificationHostConfig:
    host_file_path: Path = _get_host_file_path(host_name=host_name)
    return NotificationHostConfig(
        **load_object_from_file(
            path=host_file_path,
            default={"host_labels": {}, "service_labels": {}, "tags": {}},
        )
    )


def _get_host_file_path(config_path: Path | None = None, host_name: HostName | None = None) -> Path:
    root_path = config_path if config_path else VersionedConfigPath.LATEST_CONFIG
    if host_name:
        return root_path / "notify" / "host_config" / host_name
    return root_path / "notify" / "host_config"
