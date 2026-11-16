#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from cmk.cli.internal import Argument as CLIArgument
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Count as CLICount
from cmk.cli.internal import Declaration as CLIDeclaration
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import Reader as CLIReader
from cmk.cli.internal import Value as CLIValue
from cmk.cli.internal import Values as CLIValues

from .options import GetoptOptions, Option, spellings

type Positional = CLIArgument[object] | CLIArguments[object]


@dataclass(frozen=True, kw_only=True)
class Recorded:
    options: Sequence[Option]
    positional: Sequence[Positional]


def record(request: Callable[[CLIReader], object]) -> Recorded:
    read: list[CLIDeclaration] = []

    def given(declaration: CLIDeclaration) -> Sequence[str]:
        read.append(declaration)
        return ()

    request(CLIReader(given))
    return Recorded(
        options=[
            declaration
            for declaration in read
            if isinstance(declaration, CLIFlag | CLICount | CLIValue | CLIValues)
        ],
        positional=[
            declaration
            for declaration in read
            if isinstance(declaration, CLIArgument | CLIArguments)
        ],
    )


def assign(
    positional: Sequence[Positional], arguments: Sequence[str]
) -> Mapping[str, Sequence[str]]:
    assigned: dict[str, Sequence[str]] = {}
    unread = arguments
    for declaration in positional:
        match declaration:
            case CLIArgument(optional=False) if not unread:
                raise ValueError(f"{declaration.placeholder}: Missing argument")
            case CLIArgument():
                assigned[declaration.placeholder], unread = unread[:1], unread[1:]
            case CLIArguments():
                assigned[declaration.placeholder], unread = unread, ()
    if unread:
        raise ValueError(f"{unread[0]}: Unexpected argument")
    return assigned


def _given_option(options: GetoptOptions, option: Option, logger: logging.Logger) -> Sequence[str]:
    option_spellings = spellings(option)
    given = []
    for spec, argument in options:
        if spec not in option_spellings:
            continue
        if spec.lstrip("-") in option.deprecated_names:
            logger.warning(
                "%(deprecated)r is deprecated in favour of option %(name)r",
                {"deprecated": spec, "name": option.long},
            )
        given.append(argument)
    return given


def parsed(
    options: GetoptOptions, assigned: Mapping[str, Sequence[str]], logger: logging.Logger
) -> CLIReader:
    def given(declaration: CLIDeclaration) -> Sequence[str]:
        match declaration:
            case CLIFlag() | CLICount() | CLIValue() | CLIValues():
                return _given_option(options, declaration, logger)
            case CLIArgument() | CLIArguments():
                return assigned.get(declaration.placeholder, ())

    return CLIReader(given)
