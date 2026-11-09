#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import textwrap
from collections.abc import Callable, Mapping, Sequence
from typing import Final, override

from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Reader as CLIReader

from .options import HELP_OPTION, HELP_WIDTH, Option, OptionName

type BoundCommand = Callable[[CLIContext, CLIArgs], CLIExitCode]
"""A command's handler with the command's request already read"""


class GetoptCommand(Option):
    def __init__(
        self,
        *,
        name: str,
        long_option: OptionName,
        bind: Callable[[CLIReader], BoundCommand],
        short_help: str,
        short_option: OptionName | None = None,
        argument: bool = False,
        argument_descr: str | None = None,
        argument_optional: bool = False,
        long_help: Sequence[str] = (),
        sub_options: Sequence[Option] = (),
    ) -> None:
        super().__init__(
            long_option=long_option,
            short_help=short_help,
            short_option=short_option,
            argument=argument,
            argument_descr=argument_descr,
            argument_optional=argument_optional,
        )
        self._name: Final = name
        self.bind = bind
        self.long_help = long_help
        self.sub_options = sub_options

    @property
    @override
    def name(self) -> str:
        return self._name

    @override
    def short_getopt_specs(self) -> list[str]:
        return [
            *super().short_getopt_specs(),
            *(spec for option in self.sub_options for spec in option.short_getopt_specs()),
        ]

    @override
    def long_getopt_specs(self) -> list[str]:
        return [
            *super().long_getopt_specs(),
            *(spec for option in self.sub_options for spec in option.long_getopt_specs()),
        ]

    def long_help_text(self) -> str | None:
        if not self.long_help and not self.sub_options:
            return None

        text: list[str] = []

        option_text = "  "
        if self.short_option:
            option_text += "-%s, " % self.short_option
        option_text += "--%s " % self.long_option

        if not self.long_help:
            text.append(option_text)
        else:
            for index, paragraph in enumerate(self.long_help):
                text.append(
                    textwrap.fill(
                        paragraph,
                        width=HELP_WIDTH,
                        initial_indent=option_text if index == 0 else "    ",
                        subsequent_indent="    ",
                    )
                )

        if self.sub_options:
            sub_texts = [option.short_help_text(fmt="    %-24s") for option in self.sub_options]
            text.append("    Additional options:\n\n%s" % "\n".join(sub_texts))

        return "\n\n".join(text)


def bind[R](command: CLICommand[R], reader: CLIReader) -> BoundCommand:
    request = command.request(reader)
    return lambda context, args: command.handler(context, request, args)


def _help_order(text: str) -> str:
    return text.lstrip(" -").lower()


def _map_options(commands: Sequence[GetoptCommand]) -> Mapping[OptionName, GetoptCommand]:
    reserved = {HELP_OPTION.long_option, HELP_OPTION.short_option}
    mapped: dict[OptionName, GetoptCommand] = {}
    for command in commands:
        for name in (command.long_option, command.short_option):
            if name is None:
                continue
            if name in reserved:
                raise ValueError(f"{name!r} is the help, not the command {command.name!r}")
            if (other := mapped.get(name)) is not None:
                raise ValueError(
                    f"{name!r} is claimed by the commands {other.name!r} and {command.name!r}"
                )
            mapped[name] = command
    return mapped


class Commands:
    def __init__(
        self,
        *,
        plugins: Sequence[GetoptCommand],
        general_options: Sequence[Option],
    ) -> None:
        self._command_map: Mapping[OptionName, GetoptCommand] = _map_options(plugins)
        self._commands = plugins
        self._general_options = general_options

    def find(self, name: OptionName) -> GetoptCommand | None:
        return self._command_map.get(name)

    def _options(self) -> Sequence[Option]:
        return [HELP_OPTION, *self._commands, *self._general_options]

    def short_getopt_specs(self) -> str:
        return "".join(spec for option in self._options() for spec in option.short_getopt_specs())

    def long_getopt_specs(self) -> list[str]:
        return [spec for option in self._options() for spec in option.long_getopt_specs()]

    def help(self) -> str:
        return f"""WAYS TO CALL:
{self._short_help()}

OPTIONS:
{self._general_option_help()}

NOTES:
{self._long_help()}

"""

    def _short_help(self) -> str:
        texts = [command.short_help_text(" cmk %-36s") for command in self._commands]
        return "\n".join(sorted(texts, key=_help_order))

    def _long_help(self) -> str:
        texts = [text for command in self._commands if (text := command.long_help_text())]
        return "\n\n".join(sorted(texts, key=_help_order))

    def _general_option_help(self) -> str:
        texts = [
            option.short_help_text(fmt="  %-21s")
            for option in [HELP_OPTION, *self._general_options]
        ]
        return "\n".join(sorted(texts, key=_help_order))
