#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import getopt
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .commands import BoundCommand, Commands, DiscoveredCommand, takes_value
from .options import GetoptOptions, GlobalOptions, HELP_OPTION, read_global_options, spellings
from .readers import assign, parsed


@dataclass(frozen=True)
class _Deprecation:
    spelling: str
    replacement: str


@dataclass(frozen=True)
class RunCommand:
    command: DiscoveredCommand
    global_options: GlobalOptions
    bound: BoundCommand
    deprecations: Sequence[_Deprecation]


@dataclass(frozen=True)
class ShowHelp:
    global_options: GlobalOptions


@dataclass(frozen=True)
class InvalidArguments:
    message: str


def _args(command: DiscoveredCommand, argument: str, positional: Sequence[str]) -> Sequence[str]:
    if takes_value(command):
        return [argument, *positional]
    return positional


def _selected(
    commands: Commands, options: GetoptOptions, positional: Sequence[str]
) -> tuple[DiscoveredCommand, str] | None:
    for option, argument in options:
        if (command := commands.find(option)) is not None:
            return command, argument
    if positional and commands.default is not None:
        return commands.default, ""
    return None


def _deprecations(options: GetoptOptions, command: DiscoveredCommand) -> Sequence[_Deprecation]:
    return [
        _Deprecation(spelling=spec, replacement=option.long)
        for spec, _argument in options
        for option in command.options
        if spec in spellings(option) and spec.lstrip("-") in option.deprecated_names
    ]


def _parse(commands: Commands, argv: Sequence[str]) -> RunCommand | ShowHelp:
    options, positional = commands.getopt(argv[1:])
    global_options = read_global_options(parsed(options, {}))
    if any(option in spellings(HELP_OPTION) for option, _argument in options):
        return ShowHelp(global_options)

    match _selected(commands, options, positional):
        case None:
            return ShowHelp(global_options)
        case command, argument:
            args = _args(command, argument, positional)
            return RunCommand(
                command,
                global_options,
                command.bind(parsed(options, assign(command.positional, args))),
                _deprecations(options, command),
            )


def _rejection(argv: Sequence[str], error: Exception) -> str:
    return f"ERROR: {error} (see `{Path(argv[0]).name} --help` for valid options)\n"


def parse(commands: Commands, argv: Sequence[str]) -> RunCommand | ShowHelp | InvalidArguments:
    try:
        return _parse(commands, argv)
    except (getopt.GetoptError, ValueError) as error:
        return InvalidArguments(_rejection(argv, error))
