#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from functools import partial

from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import entry_point_prefixes as cli_entry_point_prefixes
from cmk.discover_plugins import discover_all_plugins, PluginGroup, PluginLocation

from .commands import bind, DiscoveredCommand
from .readers import RecordedOptions


def make_command[R](command: CLICommand[R]) -> DiscoveredCommand:
    recorded = RecordedOptions()
    command.request(recorded)
    return DiscoveredCommand(
        name=command.name,
        long=command.long,
        short=command.short,
        help=command.help,
        arguments=command.arguments,
        description=command.description,
        options=recorded.options,
        bind=partial(bind, command),
        default=command.default,
    )


def _named_after_its_variable[R](
    prefix: str, location: PluginLocation, command: CLICommand[R]
) -> CLICommand[R]:
    if location.name != f"{prefix}{command.name}":
        raise ValueError(f"{location} is not named after its command {command.name!r}")
    return command


def discover_commands() -> Sequence[DiscoveredCommand]:
    prefixes = cli_entry_point_prefixes()
    discovered = discover_all_plugins(
        PluginGroup.CLI,
        prefixes,
        skip_wrong_types=False,
        raise_errors=True,
    )
    return tuple(
        make_command(_named_after_its_variable(prefixes[CLICommand], location, command))
        for location, command in discovered.plugins.items()
    )
