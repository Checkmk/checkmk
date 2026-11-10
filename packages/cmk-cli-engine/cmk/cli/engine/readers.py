#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from cmk.cli.internal import Reader as CLIReader

from .options import Declaration, GetoptOptions, spellings


@dataclass(frozen=True, kw_only=True)
class Recorded:
    options: Sequence[Declaration]


def record(request: Callable[[CLIReader], object]) -> Recorded:
    read: list[Declaration] = []

    def given(declaration: Declaration) -> Sequence[str]:
        read.append(declaration)
        return ()

    request(CLIReader(given))
    return Recorded(options=read)


def _given_option(
    options: GetoptOptions, option: Declaration, logger: logging.Logger
) -> Sequence[str]:
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


def parsed(options: GetoptOptions, logger: logging.Logger) -> CLIReader:
    def given(option: Declaration) -> Sequence[str]:
        return _given_option(options, option, logger)

    return CLIReader(given)
