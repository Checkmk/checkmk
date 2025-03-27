#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Managing the available automation calls"""

import subprocess
from abc import ABC, abstractmethod
from collections.abc import Mapping

import cmk.ccc.plugin_registry
import cmk.ccc.version as cmk_version

from cmk.utils import paths
from cmk.utils.licensing.registry import get_license_state

OMDStatus = Mapping[str, int]


class AutomationCommand[T](ABC):
    """Abstract base class for all automation commands"""

    @abstractmethod
    def command_name(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def get_request(self) -> T:
        """Get request variables from environment

        In case an automation command needs to read variables from the HTTP request this has to be done
        in this method. The request produced by this function is 1:1 handed over to the execute() method.
        """
        raise NotImplementedError()

    @abstractmethod
    def execute(self, api_request: T) -> object:
        raise NotImplementedError()


class AutomationCommandRegistry(cmk.ccc.plugin_registry.Registry[type[AutomationCommand]]):
    def plugin_name(self, instance: type[AutomationCommand]) -> str:
        return instance().command_name()


automation_command_registry = AutomationCommandRegistry()


class AutomationPing(AutomationCommand[None]):
    def command_name(self) -> str:
        return "ping"

    def get_request(self) -> None:
        return None

    def _parse_omd_status(self, raw_status: str) -> OMDStatus:
        status = {key: int(val) for key, val in (el.split(" ") for el in raw_status.splitlines())}
        return status

    def _get_omd_status(self) -> OMDStatus:
        """Get the status of OMD services on the site
        0: running, 1: stopped, 5: disabled
        """

        result = subprocess.run(
            ["omd", "-v", "status", "--bare"],
            capture_output=True,
            text=True,
            check=False,
        )

        return self._parse_omd_status(result.stdout)

    def execute(self, _unused_request: None) -> dict[str, str | OMDStatus]:
        return {
            "version": cmk_version.__version__,
            "edition": cmk_version.edition(paths.omd_root).short,
            "license_state": get_license_state().name,
            "omd_status": self._get_omd_status(),
        }
