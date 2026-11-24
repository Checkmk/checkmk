#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import getopt
import textwrap
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import Reader as CLIReader
from cmk.cli.internal import Value as CLIValue

from .options import (
    ENGINE_OPTIONS,
    GetoptOptions,
    HELP_WIDTH,
    HelpColumn,
    is_required,
    long_getopt_specs,
    Option,
    placeholder,
    Positional,
    short_getopt_spec,
    short_help_text,
    spellings,
)

_COMMAND_COLUMN: Final = HelpColumn(indent=" cmk ", width=36)

_SUB_OPTION_COLUMN: Final = HelpColumn(indent="    ", width=24)

_ENGINE_OPTION_COLUMN: Final = HelpColumn(indent="  ", width=21)


@dataclass(frozen=True, kw_only=True)
class BoundCommand:
    request: object
    load: Callable[[], Callable[[CLIContext], CLIExitCode]]


type Binder = Callable[[CLIReader], BoundCommand]


@dataclass(frozen=True, kw_only=True)
class DiscoveredCommand:
    name: str
    selector: CLIFlag | CLIValue[str]
    positional: Sequence[Positional]
    description: Sequence[str]
    options: Sequence[Option]
    bind: Binder
    default: bool


def takes_value(command: DiscoveredCommand) -> bool:
    return placeholder(command.selector) is not None


def _spelled(command: DiscoveredCommand) -> str:
    return ", ".join(spellings(command.selector))


def _bracketed_unless_required(positional: Positional) -> str:
    return positional.placeholder if is_required(positional) else f"[{positional.placeholder}]"


def _spelled_argument(command: DiscoveredCommand) -> str:
    return "".join(f" {_bracketed_unless_required(each)}" for each in command.positional)


def _short_help_text(command: DiscoveredCommand) -> str:
    spelled = f" {_spelled(command)}{_spelled_argument(command)}"
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


def _check_arguments(options: Sequence[Option]) -> None:
    declared: dict[str, bool] = {}
    for option in options:
        with_argument = placeholder(option) is not None
        for spelling in spellings(option):
            if declared.setdefault(spelling, with_argument) != with_argument:
                raise ValueError(f"{spelling!r} is declared both with and without an argument")


def _default_command(commands: Sequence[DiscoveredCommand]) -> DiscoveredCommand | None:
    match [command for command in commands if command.default]:
        case []:
            return None
        case [command] if takes_value(command):
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
        self._options: Sequence[Option] = [
            *(command.selector for command in commands),
            *ENGINE_OPTIONS,
            *(option for command in commands for option in command.options),
        ]
        _check_arguments(self._options)

    def find(self, spelling: str) -> DiscoveredCommand | None:
        return self._command_map.get(spelling)

    def getopt(self, args: Sequence[str]) -> tuple[GetoptOptions, Sequence[str]]:
        return getopt.getopt(
            list(args),
            "".join(short_getopt_spec(option) for option in self._options),
            [spec for option in self._options for spec in long_getopt_specs(option)],
        )

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
