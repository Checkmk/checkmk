#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import subprocess
from collections.abc import Container
from typing import Literal

_LOGGER = logging.getLogger(__name__)


type _Command = Literal["reload", "restart"]


def reload_services_affected_by_mkp_changes() -> None:
    sync_actions: tuple[tuple[_Command, str], ...] = (
        # to see new plugins we need to restart.
        ("restart", "automation-helper"),
        ("reload", "ui-job-scheduler"),
        ("reload", "redis"),
    )

    running = _running_omd_services(*(service for _action, service in sync_actions), "apache")

    _omd_services(*sync_actions, running=running)
    # apache must come last: it should only serve requests once the services
    # above are up to date.
    _omd_services(("reload", "apache"), running=running)


def _running_omd_services(*services: str) -> Container[str]:
    # Note: at some point it'll be faster to parse `omd status -b`
    probes = {
        service_name: subprocess.Popen(
            ["omd", "status", service_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for service_name in services
    }
    return {service_name for service_name, probe in probes.items() if probe.wait() == 0}


def _omd_services(*services: tuple[_Command, str], running: Container[str]) -> None:
    """Run the given `omd` commands concurrently, skipping stopped services"""
    actions = {
        (command, service_name): subprocess.Popen(
            ["omd", command, service_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        for command, service_name in services
        if service_name in running
    }
    for (command, service_name), process in actions.items():
        _stdout, stderr = process.communicate()
        if process.returncode != 0:
            _LOGGER.error(
                "Error %(command)sing %(service_name)s: %(stderr)s",
                {
                    "command": command,
                    "service_name": service_name,
                    "stderr": stderr.decode(errors="replace").strip(),
                },
            )
