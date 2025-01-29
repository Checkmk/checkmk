#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import hashlib
import os
from logging import Logger
from typing import Literal

from cmk.utils import tty

from cmk.gui.background_job import BackgroundJobDefines

from cmk.update_config.registry import update_action_registry, UpdateAction


class UpdateBackgroundJobs(UpdateAction):
    def __call__(self, logger: Logger) -> None:
        _rename_background_job_dirs(logger)


def _rename_background_job_dirs(logger: Logger) -> None:
    """
    Hostnames can be too long, see CMK-16289.
    We now use the hash of the hostname to create the directory name.
    """
    logger.debug("       Rename directories of service discovery background job...")
    dir_prefix: Literal["service_discovery-"] = "service_discovery-"
    background_job_path = BackgroundJobDefines.base_dir
    if not os.path.exists(background_job_path):
        logger.debug(
            f"       Background job path {background_job_path} not found, skipping update step..."
        )
        return

    try:
        for item in os.listdir(background_job_path):
            if not item.startswith(dir_prefix):
                continue

            if not os.path.isdir(item_path := os.path.join(background_job_path, item)):
                continue

            new_name = rename_func(dir_prefix, item)
            new_path = os.path.join(background_job_path, new_name)
            os.rename(item_path, new_path)
            logger.debug(
                f"       Renamed: {item_path} -> {new_path}...{tty.green}Passed{tty.normal}"
            )
    except Exception as e:
        logger.warning(
            f"       File {item_path} could not be renamed...{tty.red}Failed{tty.normal}\nError: {e}"
        )


def rename_func(
    dir_prefix: Literal["service_discovery-"],
    item: str,
) -> str:
    """Create new directory name with hostname hash"""
    host_name = item.replace(dir_prefix, "")
    host_hash = hashlib.sha256(host_name.encode("utf-8")).hexdigest()
    return f"{dir_prefix}{host_name[:20]}-{host_hash}"


update_action_registry.register(
    UpdateBackgroundJobs(
        name="background_jobs",
        title="Update background jobs",
        sort_index=41,
    )
)
