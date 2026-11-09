#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging
from collections.abc import Callable, Sequence

from cmk.cli.internal import Count as CLICount
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import Value as CLIValue
from cmk.cli.internal import Values as CLIValues

from .options import Declaration, GetoptOptions, spellings


class RecordedOptions:
    """Reads nothing: records the options a command declares, in the order it reads them"""

    def __init__(self) -> None:
        self.options: list[Declaration] = []

    def flag(self, option: CLIFlag) -> bool:
        self.options.append(option)
        return False

    def count(self, option: CLICount) -> int:
        self.options.append(option)
        return 0

    def value[T](self, option: CLIValue[T]) -> T | None:
        self.options.append(option)
        return None

    def values[T](self, option: CLIValues[T]) -> Sequence[T]:
        self.options.append(option)
        return ()


def _parse[T](parse: Callable[[str], T], spec: str, argument: str) -> T:
    try:
        return parse(argument)
    except ValueError:
        raise ValueError(f"{spec}: Invalid argument") from None


class ParsedOptions:
    def __init__(self, options: GetoptOptions, logger: logging.Logger) -> None:
        self._options = options
        self._logger = logger

    def _given(self, option: Declaration) -> Sequence[tuple[str, str]]:
        given = []
        for spec, argument in self._options:
            if spec not in spellings(option):
                continue
            if spec.lstrip("-") in option.deprecated_names:
                self._logger.warning(
                    "%(deprecated)r is deprecated in favour of option %(name)r",
                    {"deprecated": spec, "name": option.long},
                )
            given.append((spec, argument))
        return given

    def flag(self, option: CLIFlag) -> bool:
        return bool(self._given(option))

    def count(self, option: CLICount) -> int:
        return len(self._given(option))

    def value[T](self, option: CLIValue[T]) -> T | None:
        given = self._given(option)
        if not given:
            return None
        return _parse(option.parse, *given[-1])

    def values[T](self, option: CLIValues[T]) -> Sequence[T]:
        return tuple(_parse(option.parse, spec, argument) for spec, argument in self._given(option))
