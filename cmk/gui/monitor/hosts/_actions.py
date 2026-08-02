#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

from cmk.gui.logged_in import LoggedInUser
from cmk.gui.monitor.command import MonitorCommands
from cmk.shared_typing.monitoring.all_hosts import MonitoringAction


class PermittedHostActions:
    """Quick actions the current user is permitted to perform on hosts.

    Every attribute the frontend needs - title, icon and prominence - is sourced
    from the monitor command registry, so an action is described in exactly one
    place. The result is narrowed down to the actions the current user may
    actually perform, so the frontend never offers an action that the backend
    would reject.

    ``supported_actions`` bounds the set to the commands the frontend has a form
    for: an action the frontend cannot execute must not show up in the table, so
    this stays an explicit list rather than the whole registry.
    """

    def __init__(
        self,
        commands: MonitorCommands,
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
            MonitoringAction(
                ident=command.ident,
                title=str(command.title),
                icon=command.icon,
            )
            for command in self._commands.permitted_for(self._user, "host", self._supported_actions)
        ]
