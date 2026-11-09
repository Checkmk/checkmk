#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import getopt
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from .commands import Commands, GetoptCommand
from .options import GetoptOptions, HELP_OPTION

_IMPLICIT_CHECK_ARGUMENT_LIMIT: Final = 2
_IMPLICIT_CHECK_COMMAND: Final = "check"


@dataclass(frozen=True)
class RunCommand:
    command: GetoptCommand
    argument: str
    options: GetoptOptions
    arguments: Sequence[str]


@dataclass(frozen=True)
class ShowHelp:
    options: GetoptOptions


@dataclass(frozen=True)
class InvalidArguments:
    message: str


def _is_implicit_check(options: GetoptOptions, arguments: Sequence[str]) -> bool:
    return (0 < len(arguments) <= _IMPLICIT_CHECK_ARGUMENT_LIMIT) or any(
        option == "--keepalive" for option, _argument in options
    )


def parse(commands: Commands, argv: Sequence[str]) -> RunCommand | ShowHelp | InvalidArguments:
    try:
        options, arguments = getopt.getopt(
            list(argv[1:]), commands.short_getopt_specs(), commands.long_getopt_specs()
        )
    except getopt.GetoptError as error:
        return InvalidArguments(
            f"ERROR: {error} (see `{Path(argv[0]).name} --help` for valid options)\n"
        )

    if any(option in HELP_OPTION.options() for option, _argument in options):
        return ShowHelp(options)

    for option, argument in options:
        if (command := commands.find(option.lstrip("-"))) is not None:
            return RunCommand(command, argument, options, arguments)

    if (
        _is_implicit_check(options, arguments)
        and (command := commands.find(_IMPLICIT_CHECK_COMMAND)) is not None
    ):
        return RunCommand(command, "", options, arguments)

    return ShowHelp(options)
