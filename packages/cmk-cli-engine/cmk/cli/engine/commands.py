#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import textwrap
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import Reader as CLIReader
from cmk.cli.internal import Value as CLIValue

from .options import (
    Declaration,
    ENGINE_OPTIONS,
    HELP_WIDTH,
    HelpColumn,
    long_getopt_specs,
    placeholder,
    short_getopt_specs,
    short_help_text,
    spellings,
)

type BoundCommand = Callable[[CLIContext, CLIArgs], CLIExitCode]

_COMMAND_COLUMN: Final = HelpColumn(indent=" cmk ", width=36)

_SUB_OPTION_COLUMN: Final = HelpColumn(indent="    ", width=24)

_ENGINE_OPTION_COLUMN: Final = HelpColumn(indent="  ", width=21)


@dataclass(frozen=True, kw_only=True)
class DiscoveredCommand:
    name: str
    selector: CLIFlag | CLIValue[str]
    arguments: CLIArguments | None
    description: Sequence[str]
    options: Sequence[Declaration]
    bind: Callable[[CLIReader], BoundCommand]
    default: bool


def bind[R](command: CLICommand[R], reader: CLIReader) -> BoundCommand:
    request = command.request(reader)
    return lambda context, args: command.handler(context, request, args)


def _spelled(command: DiscoveredCommand) -> str:
    return ", ".join(spellings(command.selector))


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
    return _COMMAND_COLUMN.fill(spelled, command.selector.help)


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
        sub_texts = [short_help_text(option, _SUB_OPTION_COLUMN) for option in command.options]
        text.append("    Additional options:\n\n%s" % "\n".join(sub_texts))

    return "\n\n".join(text)


def _map_commands(commands: Sequence[DiscoveredCommand]) -> Mapping[str, DiscoveredCommand]:
    claimants = {
        spelling: f"the option {option.long!r}"
        for option in ENGINE_OPTIONS
        for spelling in spellings(option)
    }
    mapped: dict[str, DiscoveredCommand] = {}
    for command in commands:
        for spelling in spellings(command.selector):
            if (other := claimants.get(spelling)) is not None:
                raise ValueError(
                    f"{spelling!r} is claimed by {other} and the command {command.name!r}"
                )
            claimants[spelling] = f"the command {command.name!r}"
            mapped[spelling] = command
    return mapped


def _check_arguments(declarations: Sequence[Declaration]) -> None:
    declared: dict[str, bool] = {}
    for declaration in declarations:
        requires_argument = placeholder(declaration) is not None
        for spelling in spellings(declaration):
            if declared.setdefault(spelling, requires_argument) != requires_argument:
                raise ValueError(f"{spelling!r} is declared both with and without an argument")


def _default_command(commands: Sequence[DiscoveredCommand]) -> DiscoveredCommand | None:
    match [command for command in commands if command.default]:
        case []:
            return None
        case [command] if placeholder(command.selector) is not None:
            raise ValueError(f"The default command {command.name!r} cannot require an argument")
        case [command]:
            return command
        case defaults:
            raise ValueError(f"{[command.name for command in defaults]} are all default commands")


def _help_order(text: str) -> str:
    return text.lstrip(" -").lower()


class Commands:
    def __init__(self, *, commands: Sequence[DiscoveredCommand]) -> None:
        self._commands = commands
        self._command_map = _map_commands(commands)
        self.default = _default_command(commands)
        self._declarations: Sequence[Declaration] = [
            *(command.selector for command in commands),
            *ENGINE_OPTIONS,
            *(option for command in commands for option in command.options),
        ]
        _check_arguments(self._declarations)

    def find(self, spelling: str) -> DiscoveredCommand | None:
        return self._command_map.get(spelling)

    def short_getopt_specs(self) -> str:
        return "".join(
            spec for declaration in self._declarations for spec in short_getopt_specs(declaration)
        )

    def long_getopt_specs(self) -> list[str]:
        return [
            spec for declaration in self._declarations for spec in long_getopt_specs(declaration)
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
        texts = [short_help_text(option, _ENGINE_OPTION_COLUMN) for option in ENGINE_OPTIONS]
        return "\n".join(sorted(texts, key=_help_order))
