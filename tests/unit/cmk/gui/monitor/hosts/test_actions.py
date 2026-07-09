#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence
from typing import cast

from cmk.gui.logged_in import LoggedInUser
from cmk.gui.monitor.hosts._pages._actions import PermittedHostActions
from cmk.gui.views.command.registry import CommandRegistry


class _StubPermission:
    def __init__(self, name: str) -> None:
        self.name = name


class _StubCommand:
    def __init__(
        self,
        *,
        ident: str,
        title: str,
        permission: str,
        enabled: bool = True,
    ) -> None:
        self.ident = ident
        self.title = title
        self.permission = _StubPermission(permission)
        self._enabled = enabled

    def enabled(self) -> bool:
        return self._enabled


class _StubRegistry:
    def __init__(self, commands: Iterable[_StubCommand]) -> None:
        self._commands = {command.ident: command for command in commands}

    def __contains__(self, ident: str) -> bool:
        return ident in self._commands

    def __getitem__(self, ident: str) -> _StubCommand:
        return self._commands[ident]


def _permitted(
    commands: Iterable[_StubCommand],
    granted: set[str],
    supported: Sequence[str],
) -> list[tuple[str, str]]:
    actions = PermittedHostActions(
        cast(CommandRegistry, _StubRegistry(commands)),
        cast(LoggedInUser, _StubUser(granted)),
        supported,
    ).as_models()
    return [(action.ident, action.title) for action in actions]


class _StubUser:
    def __init__(self, granted: set[str]) -> None:
        self._granted = granted

    def may(self, permission_name: str) -> bool:
        return permission_name in self._granted


def test_permitted_supported_action_is_included() -> None:
    commands = [
        _StubCommand(
            ident="acknowledge",
            title="Acknowledge problems",
            permission="action.acknowledge",
        )
    ]

    assert _permitted(commands, {"general.act", "action.acknowledge"}, ["acknowledge"]) == [
        ("acknowledge", "Acknowledge problems")
    ]


def test_action_without_permission_is_excluded() -> None:
    commands = [
        _StubCommand(
            ident="acknowledge",
            title="Acknowledge problems",
            permission="action.acknowledge",
        )
    ]

    assert _permitted(commands, {"general.act"}, ["acknowledge"]) == []


def test_unsupported_action_is_excluded() -> None:
    commands = [
        _StubCommand(
            ident="remove_comments",
            title="Remove comments",
            permission="action.addcomment",
        )
    ]

    assert _permitted(commands, {"general.act", "action.addcomment"}, ["acknowledge"]) == []


def test_disabled_action_is_excluded() -> None:
    commands = [
        _StubCommand(
            ident="reschedule",
            title="Reschedule active checks",
            permission="action.reschedule",
            enabled=False,
        )
    ]

    assert _permitted(commands, {"general.act", "action.reschedule"}, ["reschedule"]) == []


def test_no_actions_without_general_act() -> None:
    commands = [
        _StubCommand(
            ident="acknowledge",
            title="Acknowledge problems",
            permission="action.acknowledge",
        )
    ]

    assert _permitted(commands, {"action.acknowledge"}, ["acknowledge"]) == []


def test_supported_actions_preserve_declared_order() -> None:
    commands = [
        _StubCommand(
            ident="reschedule",
            title="Reschedule active checks",
            permission="action.reschedule",
        ),
        _StubCommand(
            ident="acknowledge",
            title="Acknowledge problems",
            permission="action.acknowledge",
        ),
    ]

    assert _permitted(
        commands,
        {"general.act", "action.acknowledge", "action.reschedule"},
        ["acknowledge", "reschedule"],
    ) == [
        ("acknowledge", "Acknowledge problems"),
        ("reschedule", "Reschedule active checks"),
    ]
