#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

from cmk.gui.logged_in import LoggedInUser
from cmk.gui.views.command.base import Command
from cmk.gui.views.command.registry import CommandRegistry
from cmk.shared_typing.monitoring.all_hosts import MonitoringAction


class PermittedHostActions:
    """Quick actions the current user is permitted to perform on hosts.

    Resolves an explicit list of supported action idents against the legacy
    view command registry, sourcing their titles, permissions and availability
    from it, and narrows the result down to the actions the current user may
    actually perform so the frontend never offers an action that the backend
    would reject.
    """

    def __init__(
        self,
        commands: CommandRegistry,
        user: LoggedInUser,
        supported_actions: Sequence[str],
    ) -> None:
        self._commands = commands
        self._user = user
        self._supported_actions = supported_actions

    def as_models(self) -> list[MonitoringAction]:
        if not self._user.may("general.act"):
            return []
        return [
            MonitoringAction(ident=command.ident, title=str(command.title))
            for command in self._supported_commands()
            if self._is_permitted(command)
        ]

    def _supported_commands(self) -> list[Command]:
        return [
            self._commands[ident] for ident in self._supported_actions if ident in self._commands
        ]

    def _is_permitted(self, command: Command) -> bool:
        return command.enabled() and self._user.may(command.permission.name)
