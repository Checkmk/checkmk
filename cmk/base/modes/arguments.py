#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import getopt
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from .modes import Argument, Mode, Modes, Options

_IMPLICIT_CHECK_ARGUMENT_LIMIT: Final = 2
_IMPLICIT_CHECK_MODE: Final = "check"


@dataclass(frozen=True)
class RunMode:
    mode: Mode
    argument: Argument
    options: Options
    arguments: Sequence[str]


@dataclass(frozen=True)
class ShowHelp:
    options: Options


@dataclass(frozen=True)
class InvalidArguments:
    message: str


def _is_implicit_check(options: Options, arguments: Sequence[str]) -> bool:
    return (0 < len(arguments) <= _IMPLICIT_CHECK_ARGUMENT_LIMIT) or any(
        option == "--keepalive" for option, _argument in options
    )


def parse(modes: Modes, argv: Sequence[str]) -> RunMode | ShowHelp | InvalidArguments:
    try:
        options, arguments = getopt.getopt(
            list(argv[1:]), modes.short_getopt_specs(), modes.long_getopt_specs()
        )
    except getopt.GetoptError as error:
        program = argv[0].split("/")[-1]
        return InvalidArguments(f"ERROR: {error} (see `{program} --help` for valid options)\n")

    for option, argument in options:
        if (mode := modes.find(option.lstrip("-"))) is not None:
            return RunMode(mode, argument, options, arguments)

    if (
        _is_implicit_check(options, arguments)
        and (mode := modes.find(_IMPLICIT_CHECK_MODE)) is not None
    ):
        return RunMode(mode, "", options, arguments)

    return ShowHelp(options)
