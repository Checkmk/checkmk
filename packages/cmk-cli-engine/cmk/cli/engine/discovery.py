#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import importlib
from collections.abc import Callable, Sequence
from functools import partial

from cmk.cli.internal import Argument as CLIArgument
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import entry_point_prefixes as cli_entry_point_prefixes
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import Handler as CLIHandler
from cmk.cli.internal import Value as CLIValue
from cmk.discover_plugins import discover_all_plugins, PluginGroup, PluginLocation

from .commands import bind, DiscoveredCommand, Run
from .readers import Positional, record


def _selector[R](
    command: CLICommand[R], positional: Sequence[Positional]
) -> CLIFlag | CLIValue[str]:
    match positional:
        case [CLIArgument(optional=False, placeholder=placeholder)]:
            return CLIValue(
                long=command.long,
                short=command.short,
                help=command.help,
                placeholder=placeholder,
                parse=str,
            )
        case _:
            return CLIFlag(long=command.long, short=command.short, help=command.help)


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


def _is_required(positional: Positional) -> bool:
    match positional:
        case CLIArgument(optional=False):
            return True
        case _:
            return False


def _requires_one_after_an_optional(positional: Sequence[Positional]) -> bool:
    required = [_is_required(each) for each in positional]
    return False in required and any(required[required.index(False) :])


def _reads_one_after_the_remaining(positional: Sequence[Positional]) -> bool:
    return any(isinstance(each, CLIArguments) for each in positional[:-1])


def make_command[R](command: CLICommand[R], run: Callable[[], Run[R]]) -> DiscoveredCommand:
    recorded = record(command.request)
    if len({each.placeholder for each in recorded.positional}) < len(recorded.positional):
        raise ValueError(f"{command.name!r} reads a positional argument twice")
    if _reads_one_after_the_remaining(recorded.positional):
        raise ValueError(f"{command.name!r} reads an argument after its remaining arguments")
    if _requires_one_after_an_optional(recorded.positional):
        raise ValueError(f"{command.name!r} reads a required argument after an optional one")
    return DiscoveredCommand(
        name=command.name,
        selector=_selector(command, recorded.positional),
        positional=recorded.positional,
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
