#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import importlib
from collections.abc import Callable, Sequence
from functools import partial

from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import entry_point_prefixes as cli_entry_point_prefixes
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import Handler as CLIHandler
from cmk.cli.internal import Value as CLIValue
from cmk.discover_plugins import discover_all_plugins, PluginGroup, PluginLocation

from .commands import bind, DiscoveredCommand, Run
from .readers import record


def _selector[R](command: CLICommand[R]) -> CLIFlag | CLIValue[str]:
    match command.arguments:
        case None | CLIArguments(optional=True):
            return CLIFlag(long=command.long, short=command.short, help=command.help)
        case CLIArguments(placeholder=placeholder):
            return CLIValue(
                long=command.long,
                short=command.short,
                help=command.help,
                placeholder=placeholder,
                parse=str,
            )


def _split_reference(reference: str) -> tuple[str, str]:
    module_name, _colon, object_name = reference.partition(":")
    if not module_name or not object_name.isidentifier():
        raise ValueError(f"{reference!r} does not refer to a handler as 'module:object'")
    return module_name, object_name


def load_handler[R](command: CLICommand[R]) -> CLIHandler[R]:
    module_name, object_name = _split_reference(command.handler)
    match getattr(importlib.import_module(module_name), object_name, None):
        case None:
            raise LookupError(f"{module_name} has no {object_name}")
        case CLIHandler() as handler if handler.command is command:
            return handler
        case CLIHandler() as handler:
            raise ValueError(
                f"{command.handler} handles {handler.command.name!r}, not {command.name!r}"
            )
        case other:
            raise TypeError(f"{command.handler} is a {type(other).__name__}, not a Handler")


def loaded_run[R](command: CLICommand[R]) -> Run[R]:
    return load_handler(command).run


def make_command[R](command: CLICommand[R], run: Callable[[], Run[R]]) -> DiscoveredCommand:
    recorded = record(command.request)
    return DiscoveredCommand(
        name=command.name,
        selector=_selector(command),
        arguments=command.arguments,
        description=command.description,
        options=recorded.options,
        load_handler=lambda: partial(bind, command, run()),
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
        make_command(
            _named_after_its_variable(prefixes[CLICommand], location, command),
            partial(loaded_run, command),
        )
        for location, command in discovered.plugins.items()
    )
