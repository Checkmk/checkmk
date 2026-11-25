#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from cmk.cli.internal import Argument as CLIArgument
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Count as CLICount
from cmk.cli.internal import Declaration as CLIDeclaration
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import OptionalArgument as CLIOptionalArgument
from cmk.cli.internal import Reader as CLIReader
from cmk.cli.internal import Value as CLIValue
from cmk.cli.internal import Values as CLIValues

from .options import GetoptOptions, Option, Positional, spellings


@dataclass(frozen=True, kw_only=True)
class _Recorded:
    options: Sequence[Option]
    positional: Sequence[Positional]


def record(request: Callable[[CLIReader], object]) -> _Recorded:
    read: list[CLIDeclaration] = []

    def given(declaration: CLIDeclaration) -> Sequence[str]:
        read.append(declaration)
        return ()

    request(CLIReader(given))
    return _Recorded(
        options=[
            declaration
            for declaration in read
            if isinstance(declaration, CLIFlag | CLICount | CLIValue | CLIValues)
        ],
        positional=[
            declaration
            for declaration in read
            if isinstance(declaration, CLIArgument | CLIOptionalArgument | CLIArguments)
        ],
    )


def assign(
    positional: Sequence[Positional], arguments: Sequence[str]
) -> Mapping[str, Sequence[str]]:
    assigned: dict[str, Sequence[str]] = {}
    unread = arguments
    for declaration in positional:
        match declaration:
            case CLIArgument() if not unread:
                raise ValueError(f"{declaration.placeholder}: Missing argument")
            case CLIArgument() | CLIOptionalArgument():
                assigned[declaration.placeholder], unread = unread[:1], unread[1:]
            case CLIArguments():
                assigned[declaration.placeholder], unread = unread, ()
    if unread:
        raise ValueError(f"{unread[0]}: Unexpected argument")
    return assigned


def _given_option(options: GetoptOptions, option: Option) -> Sequence[str]:
    option_spellings = spellings(option)
    return [argument for spec, argument in options if spec in option_spellings]


def parsed(options: GetoptOptions, assigned: Mapping[str, Sequence[str]]) -> CLIReader:
    def given(declaration: CLIDeclaration) -> Sequence[str]:
        match declaration:
            case CLIFlag() | CLICount() | CLIValue() | CLIValues():
                return _given_option(options, declaration)
            case CLIArgument() | CLIOptionalArgument() | CLIArguments():
                return assigned.get(declaration.placeholder, ())

    return CLIReader(given)
