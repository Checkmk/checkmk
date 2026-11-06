#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import textwrap
from collections.abc import Callable, Sequence
from typing import Final

from cmk.cli.internal import GlobalOptions as CLIGlobalOptions

OptionSpec = str
OptionName = str
ConvertFunction = Callable[[str], object]
type GetoptOptions = Sequence[tuple[OptionSpec, str]]


class Option:
    def __init__(
        self,
        *,
        long_option: str,
        short_help: str,
        short_option: str | None = None,
        # ----------------------------------------------------------------------
        # TODO: To avoid nonsensical and/or contradicting value combinations,
        # all these argument-related parameters below should actually be a
        # *single* parameter, see their intrinsic relations below.
        argument: bool = False,
        argument_descr: str | None = None,
        argument_conv: ConvertFunction | None = None,
        argument_optional: bool = False,
        repeat: bool = False,
        # ----------------------------------------------------------------------
        deprecated_long_options: set[str] | None = None,
    ) -> None:
        super().__init__()

        # We have an argument description if and only if we have an argument.
        assert (argument_descr is not None) == argument
        # Having a conversion function implies that we have an argument.
        assert (argument_conv is None) or argument
        # Being optional implies that we actually have an argument.
        assert not argument_optional or argument

        self.long_option = long_option
        self.short_help = short_help
        self.short_option = short_option
        self._deprecated_long_options = deprecated_long_options or set()

        self.repeat = repeat
        self.argument = argument
        self.argument_descr = argument_descr
        self.argument_conv = argument_conv
        self.argument_optional = argument_optional

    @property
    def name(self) -> str:
        return self.long_option

    def options(self) -> list[str]:
        options = []
        if self.short_option:
            options.append(f"-{self.short_option}")
        options.append(f"--{self.long_option}")
        options.extend(f"--{opt}" for opt in self._deprecated_long_options)
        return options

    def is_deprecated_option(self, opt_str: str) -> bool:
        return opt_str.lstrip("-") in self._deprecated_long_options

    def short_help_text(self, fmt: str) -> str:
        option_txt = " %s" % (", ".join(self.options()))

        if self.argument:
            option_txt += " "
            descr = self.argument_descr if self.argument_descr else "..."
            if self.argument_optional:
                option_txt += "[%s]" % descr
            else:
                option_txt += descr

        formated_option_txt = fmt % option_txt

        wrapper = textwrap.TextWrapper(
            initial_indent=formated_option_txt,
            subsequent_indent=" " * len(fmt % ""),
            width=80,
        )
        return wrapper.fill(self.short_help)

    def short_getopt_specs(self) -> list[str]:
        if (spec := self.short_option) is None:
            return []
        if self.argument and not self.argument_optional:
            spec += ":"
        return [spec]

    def long_getopt_specs(self) -> list[str]:
        specs = [self.long_option]
        specs.extend(self._deprecated_long_options)
        if self.argument and not self.argument_optional:
            return [f"{spec}=" for spec in specs]
        return specs


HELP_OPTION: Final = Option(long_option="help", short_option="h", short_help="Print this help")


_VERBOSE_OPTION = Option(
    long_option="verbose",
    short_option="v",
    short_help="Enable verbose output (Use twice for more)",
)

_DEBUG_OPTION = Option(
    long_option="debug",
    short_help="Let most Python exceptions raise through",
)

_PROFILE_OPTION = Option(
    long_option="profile",
    short_help="Enable profiling mode",
)


def general_options() -> Sequence[Option]:
    """The options every command accepts, see `cmk.cli.internal.GlobalOptions`"""
    return [_VERBOSE_OPTION, _DEBUG_OPTION, _PROFILE_OPTION]


def parse_general_options(all_opts: GetoptOptions) -> CLIGlobalOptions:
    """Collect the general options from the parsed command line"""
    verbosity = 0
    debug = False
    profile = False
    for option, _argument in all_opts:
        if option in _VERBOSE_OPTION.options():
            verbosity += 1
        elif option in _DEBUG_OPTION.options():
            debug = True
        elif option in _PROFILE_OPTION.options():
            profile = True
    return CLIGlobalOptions(verbosity=verbosity, debug=debug, profile=profile)
