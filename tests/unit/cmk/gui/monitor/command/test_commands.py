#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Sequence
from typing import cast

from cmk.gui.logged_in import LoggedInUser
from cmk.gui.monitor.command import (
    MonitorCommand,
    MonitorCommandRegistry,
    MonitorCommands,
    MonitorObjectType,
)
from cmk.gui.utils.speaklater import LazyString


class _LegacyPermission:
    def __init__(self, name: str) -> None:
        self.name = name


class _LegacyCommand:
    """Shaped like a view command, without importing that layer."""

    def __init__(
        self,
        *,
        ident: str,
        title: str = "A command",
        icon_name: str = "commands",
        tables: Sequence[str] = ("host", "service"),
        permission: str = "action.test",
        is_shortcut: bool = False,
        is_suggested: bool = False,
        enabled: bool = True,
    ) -> None:
        self.ident = ident
        self.title = cast(LazyString, title)
        self.icon_name = icon_name
        self.tables = tables
        self.permission = _LegacyPermission(permission)
        self.is_shortcut = is_shortcut
        self.is_suggested = is_suggested
        self.enabled: Callable[[], bool] = lambda: enabled


class _LegacySource:
    """Stands in for the legacy command registry, which is injected, not copied."""

    def __init__(self, commands: list[_LegacyCommand]) -> None:
        self._commands = commands

    def add(self, command: _LegacyCommand) -> None:
        self._commands.append(command)

    def values(self) -> Iterable[_LegacyCommand]:
        return self._commands


class _StubUser:
    def __init__(self, granted: set[str]) -> None:
        self._granted = granted

    def may(self, permission_name: str) -> bool:
        return permission_name in self._granted


def _native(
    *,
    ident: str,
    title: str = "Native command",
    icon: str = "commands",
    object_types: Iterable[MonitorObjectType] = ("host",),
    permission: str = "action.test",
) -> MonitorCommand:
    return MonitorCommand(
        ident=ident,
        title=cast(LazyString, title),
        icon=icon,
        object_types=frozenset(object_types),
        permission_name=permission,
        is_prominent=False,
        is_enabled=lambda: True,
    )


def _commands(
    legacy: _LegacySource | None = None,
    native: Iterable[MonitorCommand] = (),
) -> MonitorCommands:
    registry = MonitorCommandRegistry()
    for command in native:
        registry.register(command)
    commands = MonitorCommands(registry)
    if legacy is not None:
        commands.use_legacy_source(legacy)
    return commands


def _idents(commands: MonitorCommands, granted: set[str], wanted: Sequence[str]) -> list[str]:
    permitted = commands.permitted_for(cast(LoggedInUser, _StubUser(granted)), "host", wanted)
    return [command.ident for command in permitted]


def test_legacy_command_is_adapted() -> None:
    source = _LegacySource([_LegacyCommand(ident="acknowledge", icon_name="ack")])

    permitted = _commands(source).permitted_for(
        cast(LoggedInUser, _StubUser({"action.test"})), "host", ["acknowledge"]
    )

    assert [(command.ident, command.icon) for command in permitted] == [("acknowledge", "ack")]


def test_command_registered_after_wiring_is_still_seen() -> None:
    """The source is read on demand, so registration order must not matter."""
    source = _LegacySource([])
    commands = _commands(source)

    source.add(_LegacyCommand(ident="edit_downtimes"))

    assert _idents(commands, {"action.test"}, ["edit_downtimes"]) == ["edit_downtimes"]


def test_native_command_supersedes_a_legacy_one_of_the_same_ident() -> None:
    source = _LegacySource([_LegacyCommand(ident="acknowledge", icon_name="ack")])
    commands = _commands(source, native=[_native(ident="acknowledge", icon="native-icon")])

    permitted = commands.permitted_for(
        cast(LoggedInUser, _StubUser({"action.test"})), "host", ["acknowledge"]
    )

    assert [command.icon for command in permitted] == ["native-icon"]


def test_service_only_legacy_command_does_not_apply_to_hosts() -> None:
    source = _LegacySource([_LegacyCommand(ident="acknowledge", tables=("service",))])

    assert _idents(_commands(source), {"action.test"}, ["acknowledge"]) == []


def test_unpermitted_command_is_excluded() -> None:
    source = _LegacySource([_LegacyCommand(ident="acknowledge")])

    assert _idents(_commands(source), set(), ["acknowledge"]) == []


def test_disabled_command_is_excluded() -> None:
    source = _LegacySource([_LegacyCommand(ident="acknowledge", enabled=False)])

    assert _idents(_commands(source), {"action.test"}, ["acknowledge"]) == []


def test_unwanted_command_is_excluded() -> None:
    source = _LegacySource([_LegacyCommand(ident="remove_comments")])

    assert _idents(_commands(source), {"action.test"}, ["acknowledge"]) == []


def test_prominent_commands_come_first() -> None:
    source = _LegacySource(
        [
            _LegacyCommand(ident="reschedule"),
            _LegacyCommand(ident="acknowledge", is_suggested=True),
        ]
    )

    assert _idents(_commands(source), {"action.test"}, ["reschedule", "acknowledge"]) == [
        "acknowledge",
        "reschedule",
    ]


def test_without_a_legacy_source_only_native_commands_are_offered() -> None:
    commands = _commands(native=[_native(ident="native_only")])

    assert _idents(commands, {"action.test"}, ["native_only", "acknowledge"]) == ["native_only"]
