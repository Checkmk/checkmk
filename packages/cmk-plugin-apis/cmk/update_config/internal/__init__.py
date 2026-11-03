#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Internal update config API: the (pre-)update action plug-in types and their discovery prefixes.

This is the ``internal`` variant of the per-domain update config API (see the
plugin discovery reference in ``cmk.discover_plugins``). It is not exposed to
third-party plug-in authors; it carries the actions ``cmk-update-config`` runs
when a site is updated to a new Checkmk version.

To be discovered, a plug-in module must be placed in the ``update_config``
subdirectory of a plug-in family (``cmk/plugins/<family>/update_config/<module>.py``)
and the plug-in instance name must start with the prefix returned by
:func:`entry_point_prefixes`. Modules in the site's local hierarchy
(``cmk_addons/plugins/<family>/update_config/<module>.py``) are discovered as well.
"""

import enum
import sys
from abc import ABC, abstractmethod
from collections.abc import Mapping
from logging import Logger
from termios import tcflush, TCIFLUSH
from typing import Final


class ExpiryVersion(enum.Enum):
    """Just remove the enum values corresponding to outdated (branched off) Checkmk versions,
    and the linters will point you to all obsoleted update actions."""

    NEVER = enum.auto()
    CMK_310 = enum.auto()


class ConflictMode(enum.StrEnum):
    ASK = "ask"
    ABORT = "abort"
    FORCE = "force"


class Resume(enum.Enum):
    UPDATE = enum.auto()
    ABORT = enum.auto()

    def is_abort(self) -> bool:
        return self is Resume.ABORT

    def is_not_abort(self) -> bool:
        return self is not Resume.ABORT


_USER_INPUT_ABORT: Final = ("a", "abort")
_USER_INPUT_CONTINUE: Final = ("c", "continue")


def prompt(message: str) -> str:
    tcflush(sys.stdin, TCIFLUSH)
    return input(message)


def continue_per_users_choice(prompt_text: str) -> Resume:
    while (response := prompt(prompt_text).lower()) not in [
        *_USER_INPUT_CONTINUE,
        *_USER_INPUT_ABORT,
    ]:
        sys.stdout.write(f"Invalid input '{response}'.\n")
    if response in _USER_INPUT_CONTINUE:
        return Resume.UPDATE
    return Resume.ABORT


class UpdateAction(ABC):
    """Base class for all update actions"""

    def __init__(
        self,
        *,
        name: str,
        title: str,
        sort_index: int,
        expiry_version: ExpiryVersion,  # noqa: ARG002
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


class PreUpdateAction(ABC):
    """Base class for all pre-update actions"""

    def __init__(
        self,
        *,
        name: str,
        title: str,
        sort_index: int,
        expiry_version: ExpiryVersion,  # noqa: ARG002
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


def entry_point_prefixes() -> Mapping[type[UpdateAction] | type[PreUpdateAction], str]:
    """Return the types of plug-ins and their respective prefixes that can be discovered by Checkmk.

    Example:
    ********

    >>> for plugin_type, prefix in entry_point_prefixes().items():
    ...     print(f'{prefix}... = {plugin_type.__name__}(...)')
    update_action_... = UpdateAction(...)
    pre_update_action_... = PreUpdateAction(...)
    """
    return {UpdateAction: "update_action_", PreUpdateAction: "pre_update_action_"}
