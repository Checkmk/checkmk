#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import logging
import os
import subprocess
from collections import deque
from collections.abc import Mapping, Sequence
from logging import Logger
from pathlib import Path

from cmk.ccc.config_path import VersionedConfigPath
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.i18n import _
from cmk.ccc.store import DimSerializer, load_object_from_file
from cmk.utils.labels import Labels
from cmk.utils.notify_types import NotificationContext as NotificationContext
from cmk.utils.paths import omd_root
from cmk.utils.servicename import ServiceName
from cmk.utils.tags import TagGroupID, TagID

logger = logging.getLogger("cmk.utils.notify")

# Cap protects pathological topologies and keeps env-var sizes bounded.
# notification_script_env limits each NOTIFY_* env var to 32*PAGESIZE/2
# (≈ 64 KB on Linux). At FQDN-typical ~30-50 bytes per hostname plus a
# comma, 1000 entries sit safely below that limit and cover realistic
# Checkmk topologies (a top-of-network host rarely has more downstream
# hosts than that).
MAX_HOST_DESCENDANTS = 1000


@dataclasses.dataclass(frozen=True)
class NotificationHostConfig:
    host_labels: Labels
    service_labels: Mapping[ServiceName, Labels]
    tags: Mapping[TagGroupID, TagID]
    # Recursive descendant hostnames in BFS order. Pre-computed at activate-
    # changes time so the notification path needs no livestatus query.
    descendants: Sequence[HostName] = ()


type NotifyHostFiles = Mapping[HostName, bytes]


def build_descendants_map(
    parents_per_host: Mapping[HostName, Sequence[HostName]],
) -> Mapping[HostName, Sequence[HostName]]:
    """Resolve full descendant lists for each host from a parents mapping.

    Builds a reverse (parent → children) map, then expands each host's
    descendants in BFS order with cycle protection. Results are capped at
    MAX_HOST_DESCENDANTS to keep env-var payloads bounded.
    """
    children: dict[HostName, list[HostName]] = {}
    for host, parents in parents_per_host.items():
        for parent in parents:
            children.setdefault(parent, []).append(host)

    descendants: dict[HostName, tuple[HostName, ...]] = {}
    for host in parents_per_host:
        visited: set[HostName] = {host}
        order: list[HostName] = []
        queue: deque[HostName] = deque(children.get(host, ()))
        truncated = False
        while queue:
            if len(order) >= MAX_HOST_DESCENDANTS:
                truncated = True
                break
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            order.append(current)
            queue.extend(children.get(current, ()))
        if truncated:
            logger.warning(
                "Host %s has more than %d descendants; truncating HOSTCHILDREN list",
                host,
                MAX_HOST_DESCENDANTS,
            )
        descendants[host] = tuple(order)

    return descendants


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


def create_notify_host_files(
    config_per_host: Mapping[HostName, NotificationHostConfig],
) -> NotifyHostFiles:
    serializer = DimSerializer(pretty=False)
    return {
        host: serializer.serialize(
            dataclasses.asdict(
                NotificationHostConfig(
                    host_labels=labels.host_labels,
                    service_labels={k: v for k, v in labels.service_labels.items() if v.values()},
                    tags=labels.tags,
                    descendants=labels.descendants,
                )
            )
        )
        for host, labels in config_per_host.items()
    }


def read_notify_host_file(
    host_name: HostName,
) -> NotificationHostConfig:
    # FIXME: using "latest" here is subject to race conditions
    config_path = VersionedConfigPath.make_latest_path(omd_root)
    host_file_path: Path = make_notify_host_file_path(config_path, host_name)
    return NotificationHostConfig(
        **load_object_from_file(
            path=host_file_path,
            default={"host_labels": {}, "service_labels": {}, "tags": {}, "descendants": ()},
        )
    )


def make_notify_host_file_path(config_path: Path, host_name: HostName) -> Path:
    return config_path.joinpath("notify", "host_config", host_name)
