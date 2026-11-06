#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Callable, Sequence
from typing import Protocol

from cmk.cli.internal import Count as CLICount
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import Value as CLIValue
from cmk.cli.internal import Values as CLIValues

from .options import GetoptOptions, Option, OptionSpec


class _OptionDeclaration(Protocol):
    @property
    def long(self) -> str: ...

    @property
    def help(self) -> str: ...

    @property
    def short(self) -> str | None: ...

    @property
    def deprecated_names(self) -> frozenset[str]: ...


def _option(
    declaration: _OptionDeclaration, *, placeholder: str | None = None, repeat: bool = False
) -> Option:
    return Option(
        long_option=declaration.long,
        short_help=declaration.help,
        short_option=declaration.short,
        argument=placeholder is not None,
        argument_descr=placeholder,
        repeat=repeat,
        deprecated_long_options=set(declaration.deprecated_names),
    )


def _flag_option(declaration: CLIFlag) -> Option:
    return _option(declaration)


def _count_option(declaration: CLICount) -> Option:
    return _option(declaration, repeat=True)


def _value_option[T](declaration: CLIValue[T]) -> Option:
    return _option(declaration, placeholder=declaration.placeholder)


def _values_option[T](declaration: CLIValues[T]) -> Option:
    return _option(declaration, placeholder=declaration.placeholder, repeat=True)


class RecordedOptions:
    """Reads nothing: records the options a command declares, in the order it reads them"""

    def __init__(self) -> None:
        self.options: list[Option] = []

    def flag(self, option: CLIFlag) -> bool:
        self.options.append(_flag_option(option))
        return False

    def count(self, option: CLICount) -> int:
        self.options.append(_count_option(option))
        return 0

    def value[T](self, option: CLIValue[T]) -> T | None:
        self.options.append(_value_option(option))
        return None

    def values[T](self, option: CLIValues[T]) -> Sequence[T]:
        self.options.append(_values_option(option))
        return ()


def _parse[T](parse: Callable[[str], T], spec: OptionSpec, argument: str) -> T:
    try:
        return parse(argument)
    except ValueError:
        raise ValueError(f"{spec}: Invalid argument")


class ParsedOptions:
    """Reads a command's options off the parsed command line"""

    def __init__(self, options: GetoptOptions, logger: logging.Logger) -> None:
        self._options = options
        self._logger = logger

    def _given(self, option: Option) -> Sequence[tuple[OptionSpec, str]]:
        given = []
        for spec, argument in self._options:
            if spec not in option.options():
                continue
            if option.is_deprecated_option(spec):
                self._logger.warning(
                    "%(deprecated)r is deprecated in favour of option %(name)r",
                    {"deprecated": spec, "name": option.name},
                )
            given.append((spec, argument))
        return given

    def flag(self, option: CLIFlag) -> bool:
        return bool(self._given(_flag_option(option)))

    def count(self, option: CLICount) -> int:
        return len(self._given(_count_option(option)))

    def value[T](self, option: CLIValue[T]) -> T | None:
        given = self._given(_value_option(option))
        if not given:
            return None
        return _parse(option.parse, *given[-1])

    def values[T](self, option: CLIValues[T]) -> Sequence[T]:
        return tuple(
            _parse(option.parse, spec, argument)
            for spec, argument in self._given(_values_option(option))
        )
