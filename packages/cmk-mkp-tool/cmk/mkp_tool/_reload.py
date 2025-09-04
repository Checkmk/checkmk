#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import subprocess
from typing import Literal

_LOGGER = logging.getLogger(__name__)


def reload_services_affected_by_mkp_changes() -> None:
    # order matters :-(
    _omd_service("restart", "automation-helper")  # to see new plugins we need to restart.
    _omd_service("reload", "ui-job-scheduler")
    _omd_service("reload", "redis")
    _omd_service("reload", "apache")


def _omd_service(command: Literal["reload", "restart"], service_name: str) -> None:
    try:
        subprocess.run(["omd", "status", service_name], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        return

    try:
        subprocess.run(["omd", command, service_name], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        _LOGGER.error("Error %sing %s", command, service_name, exc_info=True)
