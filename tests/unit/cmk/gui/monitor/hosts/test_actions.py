#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence
from typing import cast

from cmk.gui.logged_in import LoggedInUser
from cmk.gui.monitor.command import (
    MonitorCommand,
    MonitorCommandRegistry,
    MonitorCommands,
    MonitorObjectType,
)
from cmk.gui.monitor.hosts._actions import PermittedHostActions
from cmk.gui.utils.speaklater import LazyString
from cmk.shared_typing.monitoring.all_hosts import MonitoringAction


def _command(
    *,
    ident: str,
    title: str,
    permission: str,
    icon: str = "commands",
    object_types: Iterable[MonitorObjectType] = ("host", "service"),
    is_prominent: bool = False,
    enabled: bool = True,
) -> MonitorCommand:
    return MonitorCommand(
        ident=ident,
        title=cast(LazyString, title),
        icon=icon,
        object_types=frozenset(object_types),
        permission_name=permission,
        is_prominent=is_prominent,
        is_enabled=lambda: enabled,
    )


class _StubUser:
    def __init__(self, granted: set[str]) -> None:
        self._granted = granted

    def may(self, permission_name: str) -> bool:
        return permission_name in self._granted


def _models(
    commands: Iterable[MonitorCommand],
    granted: set[str],
    supported: Sequence[str],
) -> list[MonitoringAction]:
    registry = MonitorCommandRegistry()
    for command in commands:
        registry.register(command)
    return PermittedHostActions(
        MonitorCommands(registry),
        cast(LoggedInUser, _StubUser(granted)),
        supported,
    ).as_models()


def _permitted(
    commands: Iterable[MonitorCommand],
    granted: set[str],
    supported: Sequence[str],
) -> list[tuple[str, str]]:
    return [(action.ident, action.title) for action in _models(commands, granted, supported)]


def test_permitted_supported_action_is_included() -> None:
    commands = [
        _command(
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
        _command(
            ident="acknowledge",
            title="Acknowledge problems",
            permission="action.acknowledge",
        )
    ]

    assert _permitted(commands, {"general.act"}, ["acknowledge"]) == []


def test_unsupported_action_is_excluded() -> None:
    commands = [
        _command(
            ident="remove_comments",
            title="Remove comments",
            permission="action.addcomment",
        )
    ]

    assert _permitted(commands, {"general.act", "action.addcomment"}, ["acknowledge"]) == []


def test_disabled_action_is_excluded() -> None:
    commands = [
        _command(
            ident="reschedule",
            title="Reschedule active checks",
            permission="action.reschedule",
            enabled=False,
        )
    ]

    assert _permitted(commands, {"general.act", "action.reschedule"}, ["reschedule"]) == []


def test_no_actions_without_general_act() -> None:
    commands = [
        _command(
            ident="acknowledge",
            title="Acknowledge problems",
            permission="action.acknowledge",
        )
    ]

    assert _permitted(commands, {"action.acknowledge"}, ["acknowledge"]) == []


def test_supported_actions_preserve_declared_order() -> None:
    commands = [
        _command(
            ident="reschedule",
            title="Reschedule active checks",
            permission="action.reschedule",
        ),
        _command(
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


def test_icon_is_taken_from_the_registry() -> None:
    commands = [
        _command(
            ident="acknowledge",
            title="Acknowledge problems",
            permission="action.acknowledge",
            icon="ack",
        )
    ]

    actions = _models(commands, {"general.act", "action.acknowledge"}, ["acknowledge"])

    assert [action.icon for action in actions] == ["ack"]


def test_service_only_command_is_excluded() -> None:
    commands = [
        _command(
            ident="acknowledge",
            title="Acknowledge problems",
            permission="action.acknowledge",
            object_types=("service",),
        )
    ]

    assert _permitted(commands, {"general.act", "action.acknowledge"}, ["acknowledge"]) == []


def test_prominent_commands_are_offered_first() -> None:
    commands = [
        _command(
            ident="reschedule",
            title="Reschedule active checks",
            permission="action.reschedule",
        ),
        _command(
            ident="acknowledge",
            title="Acknowledge problems",
            permission="action.acknowledge",
            is_prominent=True,
        ),
    ]

    assert _permitted(
        commands,
        {"general.act", "action.acknowledge", "action.reschedule"},
        ["reschedule", "acknowledge"],
    ) == [
        ("acknowledge", "Acknowledge problems"),
        ("reschedule", "Reschedule active checks"),
    ]
