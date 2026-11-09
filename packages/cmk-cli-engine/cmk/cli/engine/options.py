#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import textwrap
from collections.abc import Sequence
from typing import Final

from cmk.cli.internal import Count as CLICount
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import Value as CLIValue
from cmk.cli.internal import Values as CLIValues

type GetoptOptions = Sequence[tuple[str, str]]

type Declaration = CLIFlag | CLICount | CLIValue[object] | CLIValues[object]

HELP_WIDTH: Final = 80

HELP_OPTION: Final = CLIFlag(long="help", short="h", help="Print this help")

_VERBOSE_OPTION: Final = CLICount(
    long="verbose",
    short="v",
    help="Enable verbose output (Use twice for more)",
)

_DEBUG_OPTION: Final = CLIFlag(long="debug", help="Let most Python exceptions raise through")

_PROFILE_OPTION: Final = CLIFlag(long="profile", help="Enable profiling mode")

LOG_FILE_OPTION: Final = CLIValue(
    long="log-file",
    help="Log to the given file (with timestamps) instead of stderr",
    placeholder="PATH",
    parse=str,
)

GENERAL_OPTIONS: Final[Sequence[Declaration]] = (
    _VERBOSE_OPTION,
    _DEBUG_OPTION,
    _PROFILE_OPTION,
    LOG_FILE_OPTION,
)


def spellings(option: Declaration) -> Sequence[str]:
    return [
        *([] if option.short is None else [f"-{option.short}"]),
        f"--{option.long}",
        *(f"--{name}" for name in sorted(option.deprecated_names)),
    ]


def placeholder(option: Declaration) -> str | None:
    match option:
        case CLIValue() | CLIValues():
            return option.placeholder
        case CLIFlag() | CLICount():
            return None


def short_getopt_specs(option: Declaration) -> Sequence[str]:
    if option.short is None:
        return []
    return [option.short if placeholder(option) is None else f"{option.short}:"]


def long_getopt_specs(option: Declaration) -> Sequence[str]:
    suffix = "" if placeholder(option) is None else "="
    return [f"{name}{suffix}" for name in (option.long, *sorted(option.deprecated_names))]


def help_line(spelled: str, help_text: str, fmt: str) -> str:
    return textwrap.fill(
        help_text,
        width=HELP_WIDTH,
        initial_indent=fmt % spelled,
        subsequent_indent=" " * len(fmt % ""),
    )


def short_help_text(option: Declaration, fmt: str) -> str:
    argument = placeholder(option)
    spelled = " " + ", ".join(spellings(option)) + ("" if argument is None else f" {argument}")
    return help_line(spelled, option.help, fmt)


def parse_general_options(all_opts: GetoptOptions) -> CLIGlobalOptions:
    verbosity = 0
    debug = False
    profile = False
    for option, _argument in all_opts:
        if option in spellings(_VERBOSE_OPTION):
            verbosity += 1
        elif option in spellings(_DEBUG_OPTION):
            debug = True
        elif option in spellings(_PROFILE_OPTION):
            profile = True
    return CLIGlobalOptions(verbosity=verbosity, debug=debug, profile=profile)
