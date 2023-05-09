#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Managing the available automation calls"""

import abc
from typing import Dict, Type, Any

import cmk.utils.version as cmk_version
import cmk.utils.plugin_registry


class AutomationCommand(metaclass=abc.ABCMeta):
    """Abstract base class for all automation commands"""
    @abc.abstractmethod
    def command_name(self) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_request(self) -> Any:
        """Get request variables from environment

        In case an automation command needs to read variables from the HTTP request this has to be done
        in this method. The request produced by this function is 1:1 handed over to the execute() method."""
        raise NotImplementedError()

    @abc.abstractmethod
    def execute(self, request: Any) -> Any:
        raise NotImplementedError()


class AutomationCommandRegistry(cmk.utils.plugin_registry.Registry[Type[AutomationCommand]]):
    def plugin_name(self, instance: Type[AutomationCommand]) -> str:
        return instance().command_name()


automation_command_registry = AutomationCommandRegistry()


@automation_command_registry.register
class AutomationPing(AutomationCommand):
    def command_name(self) -> str:
        return "ping"

    def get_request(self) -> None:
        return None

    def execute(self, _unused_request: None) -> Dict[str, str]:
        return {
            "version": cmk_version.__version__,
            "edition": cmk_version.edition_short(),
        }
