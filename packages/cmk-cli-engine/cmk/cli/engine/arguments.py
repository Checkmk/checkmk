#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import getopt
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions

from .commands import Commands, DiscoveredCommand
from .options import GetoptOptions, HELP_OPTION, read_global_options, spellings
from .readers import ParsedOptions

_IMPLICIT_CHECK_ARGUMENT_LIMIT: Final = 2
_IMPLICIT_CHECK_COMMAND: Final = "check"


@dataclass(frozen=True)
class RunCommand:
    command: DiscoveredCommand
    global_options: CLIGlobalOptions
    options: GetoptOptions
    args: CLIArgs


@dataclass(frozen=True)
class ShowHelp:
    global_options: CLIGlobalOptions


@dataclass(frozen=True)
class InvalidArguments:
    message: str


def _args(command: DiscoveredCommand, argument: str, positional: Sequence[str]) -> CLIArgs:
    match command.arguments:
        case None:
            return ()
        case CLIArguments(optional=True):
            return positional
        case CLIArguments():
            return [argument]


def _is_implicit_check(options: GetoptOptions, positional: Sequence[str]) -> bool:
    return (0 < len(positional) <= _IMPLICIT_CHECK_ARGUMENT_LIMIT) or any(
        option == "--keepalive" for option, _argument in options
    )


def _selected(
    commands: Commands, options: GetoptOptions, positional: Sequence[str]
) -> tuple[DiscoveredCommand, str] | None:
    for option, argument in options:
        if (command := commands.find(option.lstrip("-"))) is not None:
            return command, argument
    if (
        _is_implicit_check(options, positional)
        and (command := commands.find(_IMPLICIT_CHECK_COMMAND)) is not None
    ):
        return command, ""
    return None


def _parse(
    commands: Commands, argv: Sequence[str], logger: logging.Logger
) -> RunCommand | ShowHelp:
    options, positional = getopt.getopt(
        list(argv[1:]), commands.short_getopt_specs(), commands.long_getopt_specs()
    )
    global_options = read_global_options(ParsedOptions(options, logger))
    if any(option in spellings(HELP_OPTION) for option, _argument in options):
        return ShowHelp(global_options)

    match _selected(commands, options, positional):
        case None:
            return ShowHelp(global_options)
        case command, argument:
            return RunCommand(
                command, global_options, options, _args(command, argument, positional)
            )


def rejection(argv: Sequence[str], error: Exception) -> InvalidArguments:
    return InvalidArguments(
        f"ERROR: {error} (see `{Path(argv[0]).name} --help` for valid options)\n"
    )


def parse(
    commands: Commands, argv: Sequence[str], logger: logging.Logger
) -> RunCommand | ShowHelp | InvalidArguments:
    try:
        return _parse(commands, argv, logger)
    except (getopt.GetoptError, ValueError) as error:
        return rejection(argv, error)
