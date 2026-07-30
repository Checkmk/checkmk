#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Iterator

from cmk.gui.logged_in import LoggedInUser

from ._legacy import LegacyCommand, LegacyCommandSource
from ._registry import (
    monitor_command_registry,
    MonitorCommand,
    MonitorCommandRegistry,
    MonitorObjectType,
)


class MonitorCommands:
    """The commands the monitoring pages may offer on a host or service.

    Combines the commands registered natively in this domain with the legacy view commands,
    whose registry is injected as a source and read when a page asks. Reading on demand
    rather than copying at wiring time means a command registered later - by an edition, for
    instance - is picked up without the wiring order mattering, and the two registries
    cannot drift apart.
    """

    def __init__(self, native: MonitorCommandRegistry) -> None:
        self._native = native
        self._legacy: LegacyCommandSource | None = None

    def use_legacy_source(self, source: LegacyCommandSource) -> None:
        self._legacy = source

    def permitted_for(
        self,
        user: LoggedInUser,
        object_type: MonitorObjectType,
        idents: Iterable[str],
    ) -> list[MonitorCommand]:
        """The named commands the user may run on this object type, prominent ones first.

        Callers name the commands they support instead of taking everything on offer, so a
        command no caller can execute never reaches a page. Ordering follows each command's
        own prominence, keeping the caller's order within a group.
        """
        available = self._available()
        commands = [
            command
            for ident in idents
            if (command := available.get(ident)) is not None
            and command.applies_to(object_type)
            and command.is_permitted_for(user)
        ]
        return sorted(commands, key=lambda command: 0 if command.is_prominent else 1)

    def _available(self) -> dict[str, MonitorCommand]:
        # Natively registered commands win, so this domain can supersede a legacy one.
        commands = {command.ident: command for command in self._legacy_commands()}
        commands.update({command.ident: command for command in self._native.values()})
        return commands

    def _legacy_commands(self) -> Iterator[MonitorCommand]:
        if self._legacy is None:
            return
        for command in self._legacy.values():
            yield self._adapt(command)

    @staticmethod
    def _adapt(command: LegacyCommand) -> MonitorCommand:
        object_types: frozenset[MonitorObjectType] = frozenset(
            object_type for object_type in ("host", "service") if object_type in command.tables
        )
        return MonitorCommand(
            ident=command.ident,
            title=command.title,
            icon=str(command.icon_name),
            object_types=object_types,
            permission_name=command.permission.name,
            is_prominent=command.is_shortcut or command.is_suggested,
            is_enabled=command.enabled,
        )


monitor_commands = MonitorCommands(monitor_command_registry)
