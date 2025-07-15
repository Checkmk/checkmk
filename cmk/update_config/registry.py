#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import ABC, abstractmethod
from logging import Logger
from typing import Final, override

from cmk.ccc.plugin_registry import Registry
from cmk.update_config.plugins.pre_actions.utils import ConflictMode


class UpdateAction(ABC):
    """Base class for all update actions"""

    def __init__(
        self,
        *,
        name: str,
        title: str,
        sort_index: int,
        continue_on_failure: bool = True,
    ) -> None:
        """
        :param name: the internal name of the update action, has to be unique
        :param title: the string printed before executing the action, informational only
        :param sort_index: a relative index of the action, actions with smaller indices are executed first
        :param continue_on_failure: If True, the update continues even after an exception from __call__().
        """
        self.name: Final = name
        self.title: Final = title
        self.sort_index: Final = sort_index
        self.continue_on_failure: Final = continue_on_failure

    @abstractmethod
    def __call__(self, logger: Logger) -> None:
        """
        Execute the update action.
        Raising an exception will abort the config update, unless continue_on_failure is True.
        """


class UpdateActionRegistry(Registry[UpdateAction]):
    @override
    def plugin_name(self, instance: UpdateAction) -> str:
        return instance.name


update_action_registry = UpdateActionRegistry()


class PreUpdateAction(ABC):
    """Base class for all pre-update actions"""

    def __init__(
        self,
        *,
        name: str,
        title: str,
        sort_index: int,
    ) -> None:
        """
        :param name: the internal name of the pre-update action, has to be unique
        :param title: the string printed before executing the action, informational only
        :param sort_index: a relative index of the action, actions with smaller indices are executed first
        """
        self.name: Final = name
        self.title: Final = title
        self.sort_index: Final = sort_index

    @abstractmethod
    def __call__(self, logger: Logger, conflict_mode: ConflictMode) -> None:
        """
        Execute the pre-update action.
        Raising an exception will abort the config update.
        """


class PreUpdateActionRegistry(Registry[PreUpdateAction]):
    @override
    def plugin_name(self, instance: PreUpdateAction) -> str:
        return instance.name


pre_update_action_registry = PreUpdateActionRegistry()
