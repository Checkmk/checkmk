#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import entry_point_prefixes as cli_entry_point_prefixes
from cmk.cli.internal import Option as CLIOption
from cmk.discover_plugins import discover_all_plugins, PluginGroup, PluginLocation

from .commands import GetoptCommand
from .options import Option


def make_option(option: CLIOption) -> Option:
    """Build the engine's option from its API declaration"""
    return Option(
        long_option=option.long,
        short_help=option.help,
        short_option=option.short,
        argument=option.argument is not None,
        argument_descr=option.argument,
        argument_conv=option.parse,
        argument_optional=option.argument_optional,
        repeat=option.repeat,
        deprecated_long_options=set(option.deprecated_names),
    )


def make_command(command: CLICommand) -> GetoptCommand:
    """Build the engine's command from its API declaration"""
    arguments = command.arguments
    return GetoptCommand(
        name=command.name,
        long_option=command.long,
        handler_function=command.handler_function,
        short_help=command.help,
        short_option=command.short,
        argument=arguments is not None,
        argument_descr=None if arguments is None else arguments.placeholder,
        argument_optional=arguments is not None and arguments.optional,
        long_help=list(command.description) if command.description is not None else None,
        sub_options=[make_option(option) for option in command.sub_options],
    )


def _named_after_its_variable(location: PluginLocation, command: CLICommand) -> CLICommand:
    if location.name != f"{cli_entry_point_prefixes()[CLICommand]}{command.name}":
        raise ValueError(f"{location} is not named after its command {command.name!r}")
    return command


def discover_commands() -> Sequence[GetoptCommand]:
    discovered = discover_all_plugins(
        PluginGroup.CLI,
        cli_entry_point_prefixes(),
        skip_wrong_types=False,
        raise_errors=True,
    )
    return tuple(
        make_command(_named_after_its_variable(location, command))
        for location, command in discovered.plugins.items()
    )
