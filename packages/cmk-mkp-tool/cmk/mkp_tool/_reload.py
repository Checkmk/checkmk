#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import subprocess

_LOGGER = logging.getLogger(__name__)


def reload_services_affected_by_mkp_changes() -> None:
    # order matters :-(
    _reload_service("automation-helper")
    _reload_service("ui-job-scheduler")
    _reload_service("redis")
    _reload_service("apache")


def _reload_service(service_name: str) -> None:
    try:
        subprocess.run(["omd", "status", service_name], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        return

    try:
        subprocess.run(["omd", "reload", service_name], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        _LOGGER.error("Error reloading %s", service_name, exc_info=True)
