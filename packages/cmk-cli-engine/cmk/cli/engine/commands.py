#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import textwrap
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Reader as CLIReader

from .options import (
    Declaration,
    GENERAL_OPTIONS,
    help_line,
    HELP_OPTION,
    HELP_WIDTH,
    long_getopt_specs,
    short_getopt_specs,
    short_help_text,
)

type BoundCommand = Callable[[CLIContext, CLIArgs], CLIExitCode]
"""A command's handler with the command's request already read"""


@dataclass(frozen=True, kw_only=True)
class DiscoveredCommand:
    name: str
    long: str
    short: str | None
    help: str
    arguments: CLIArguments | None
    description: Sequence[str]
    options: Sequence[Declaration]
    bind: Callable[[CLIReader], BoundCommand]


def bind[R](command: CLICommand[R], reader: CLIReader) -> BoundCommand:
    request = command.request(reader)
    return lambda context, args: command.handler(context, request, args)


def _requires_argument(command: DiscoveredCommand) -> bool:
    return command.arguments is not None and not command.arguments.optional


def _short_getopt_specs(command: DiscoveredCommand) -> Sequence[str]:
    if command.short is None:
        return []
    return [f"{command.short}:" if _requires_argument(command) else command.short]


def _long_getopt_specs(command: DiscoveredCommand) -> Sequence[str]:
    return [f"{command.long}=" if _requires_argument(command) else command.long]


def _spelled(command: DiscoveredCommand) -> str:
    return f"{'' if command.short is None else f'-{command.short}, '}--{command.long}"


def _spelled_argument(arguments: CLIArguments | None) -> str:
    match arguments:
        case None:
            return ""
        case CLIArguments(placeholder=placeholder, optional=True):
            return f" [{placeholder}]"
        case CLIArguments(placeholder=placeholder):
            return f" {placeholder}"


def _short_help_text(command: DiscoveredCommand) -> str:
    spelled = f" {_spelled(command)}{_spelled_argument(command.arguments)}"
    return help_line(spelled, command.help, " cmk %-36s")


def _long_help_text(command: DiscoveredCommand) -> str | None:
    if not command.description and not command.options:
        return None

    option_text = f"  {_spelled(command)} "
    text = [
        textwrap.fill(
            paragraph,
            width=HELP_WIDTH,
            initial_indent=option_text if index == 0 else "    ",
            subsequent_indent="    ",
        )
        for index, paragraph in enumerate(command.description)
    ] or [option_text]

    if command.options:
        sub_texts = [short_help_text(option, "    %-24s") for option in command.options]
        text.append("    Additional options:\n\n%s" % "\n".join(sub_texts))

    return "\n\n".join(text)


def _map_commands(commands: Sequence[DiscoveredCommand]) -> Mapping[str, DiscoveredCommand]:
    reserved = {HELP_OPTION.long, HELP_OPTION.short}
    mapped: dict[str, DiscoveredCommand] = {}
    for command in commands:
        for name in (command.long, command.short):
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


def _help_order(text: str) -> str:
    return text.lstrip(" -").lower()


class Commands:
    def __init__(self, *, plugins: Sequence[DiscoveredCommand]) -> None:
        self._commands = plugins
        self._command_map = _map_commands(plugins)
        self._options = [
            HELP_OPTION,
            *GENERAL_OPTIONS,
            *(option for command in plugins for option in command.options),
        ]

    def find(self, name: str) -> DiscoveredCommand | None:
        return self._command_map.get(name)

    def short_getopt_specs(self) -> str:
        return "".join(
            [
                *(spec for command in self._commands for spec in _short_getopt_specs(command)),
                *(spec for option in self._options for spec in short_getopt_specs(option)),
            ]
        )

    def long_getopt_specs(self) -> list[str]:
        return [
            *(spec for command in self._commands for spec in _long_getopt_specs(command)),
            *(spec for option in self._options for spec in long_getopt_specs(option)),
        ]

    def help(self) -> str:
        return f"""WAYS TO CALL:
{self._short_help()}

OPTIONS:
{self._general_option_help()}

NOTES:
{self._long_help()}

"""

    def _short_help(self) -> str:
        texts = [_short_help_text(command) for command in self._commands]
        return "\n".join(sorted(texts, key=_help_order))

    def _long_help(self) -> str:
        texts = [text for command in self._commands if (text := _long_help_text(command))]
        return "\n\n".join(sorted(texts, key=_help_order))

    def _general_option_help(self) -> str:
        texts = [short_help_text(option, "  %-21s") for option in (HELP_OPTION, *GENERAL_OPTIONS)]
        return "\n".join(sorted(texts, key=_help_order))
