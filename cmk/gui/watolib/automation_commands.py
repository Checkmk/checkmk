#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

"""Managing the available automation calls"""

from abc import ABC, abstractmethod
from typing import override, TypedDict

import cmk.ccc.plugin_registry
import cmk.ccc.version as cmk_version
from cmk.ccc.site import get_agent_receiver_port, get_omd_config
from cmk.gui.config import Config
from cmk.gui.http import Request
from cmk.gui.watolib import wire_format
from cmk.licensing.registry import get_license_state
from cmk.utils import paths


class OMDStatus(TypedDict):
    """Only rabbitmq: 0 enabled, 5 disabled. Key name kept for older central sites."""

    rabbitmq: int


class AutomationCommand[T](ABC):
    """Abstract base class for all automation commands"""

    @abstractmethod
    def command_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_request(self, config: Config, request: Request) -> T:
        """Get request variables from environment

        In case an automation command needs to read variables from the HTTP request this has to be done
        in this method. The request produced by this function is 1:1 handed over to the execute() method.
        """
        raise NotImplementedError

    @abstractmethod
    def execute(self, api_request: T) -> object:
        raise NotImplementedError

    def needs_configuration_lock(self) -> bool:
        """Whether the configuration is locked while the command is executed

        Commands which only start or observe a background job that locks the configuration on
        its own must not hold the lock. Otherwise the job could not start working before the
        request finishes."""
        return True


class AutomationCommandRegistry(cmk.ccc.plugin_registry.Registry[type[AutomationCommand]]):
    @override
    def plugin_name(self, instance: type[AutomationCommand]) -> str:
        return instance().command_name()


automation_command_registry = AutomationCommandRegistry()


class AutomationPing(AutomationCommand[None]):
    """Answer the central site's ping with version, edition and license state

    "omd_status" only tells whether rabbitmq is enabled. It does not hold the
    state of all site services, despite its name.
    """

    @override
    def command_name(self) -> str:
        return "ping"

    @override
    def get_request(self, config: Config, request: Request) -> None:
        return None

    def _get_omd_status(self) -> OMDStatus:
        """Tell the central site whether rabbitmq is disabled (5) on this site

        Same rule as etc/init.d/rabbitmq. Running `omd status` for this is too slow
        when the central site pings many sites on one server at once.
        """
        hub_enabled = get_omd_config(paths.omd_root).get("CONFIG_PIGGYBACK_HUB") == "on"
        return {"rabbitmq": 0 if hub_enabled else 5}

    @override
    def execute(self, _unused_request: None) -> dict[str, str | OMDStatus]:
        return {
            "version": cmk_version.__version__,
            "edition": cmk_version.edition(paths.omd_root).short,
            "license_state": wire_format.license_state_to_ping_string(
                get_license_state(paths.omd_root)
            ),
            "omd_status": self._get_omd_status(),
        }


class AutomationGetAgentReceiverPort(AutomationCommand[None]):
    @override
    def command_name(self) -> str:
        return "get-agent-receiver-port"

    @override
    def get_request(self, config: Config, request: Request) -> None:
        return None

    @override
    def execute(self, _unused_request: None) -> int:
        return get_agent_receiver_port(paths.omd_root)
