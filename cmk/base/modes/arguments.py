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


def parse(modes: Modes, argv: Sequence[str]) -> RunMode | ShowHelp | InvalidArguments:
    try:
        options, arguments = getopt.getopt(
            list(argv[1:]), modes.short_getopt_specs(), modes.long_getopt_specs()
        )
    except getopt.GetoptError as error:
        program = argv[0].split("/")[-1]
        return InvalidArguments(f"ERROR: {error} (see `{program} --help` for valid options)\n")

    for option, argument in options:
        if modes.exists(name := option.lstrip("-")):
            return RunMode(modes.get(name), argument, options, arguments)

    if (arguments and len(arguments) <= _IMPLICIT_CHECK_ARGUMENT_LIMIT) or "--keepalive" in [
        option for option, _argument in options
    ]:
        return RunMode(modes.get("check"), "", options, arguments)

    return ShowHelp(options)
