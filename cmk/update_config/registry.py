#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import ABC, abstractmethod
from logging import Logger
from typing import Final

from cmk.utils.plugin_registry import Registry

from cmk.update_config.plugins.pre_actions.utils import ConflictMode

from .update_state import UpdateActionState


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
        self.name: Final = name
        self.title: Final = title
        self.sort_index: Final = sort_index
        self.continue_on_failure: Final = continue_on_failure

    @abstractmethod
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        """Execute the update action"""


class UpdateActionRegistry(Registry[UpdateAction]):
    def plugin_name(self, instance: UpdateAction) -> str:
        return instance.name


update_action_registry = UpdateActionRegistry()


class PreUpdateAction(ABC):
    """Base class for all pre update actions"""

    def __init__(
        self,
        *,
        name: str,
        title: str,
        sort_index: int,
    ) -> None:
        self.name: Final = name
        self.title: Final = title
        self.sort_index: Final = sort_index

    @abstractmethod
    def __call__(self, conflict_mode: ConflictMode) -> None:
        """Execute the update action"""


class PreUpdateActionRegistry(Registry[PreUpdateAction]):
    def plugin_name(self, instance: PreUpdateAction) -> str:
        return instance.name


pre_update_action_registry = PreUpdateActionRegistry()
