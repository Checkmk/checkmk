#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from typing import NoReturn

import pytest

from cmk.cli.engine.commands import Commands as CLICommands
from cmk.cli.engine.commands import DiscoveredCommand as CLIDiscoveredCommand
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import no_options as cli_no_options
from cmk.cli.internal import Reader as CLIReader
from cmk.cli.internal import Value as CLIValue

from ._commands import command_with, HANDED_IN


def _never(*_args: object, **_kwargs: object) -> NoReturn:
    raise AssertionError("the command must not run")


def _command(
    long: str,
    short: str | None = None,
    *,
    request: Callable[[CLIReader], object] = cli_no_options,
    arguments: CLIArguments | None = None,
    default: bool = False,
) -> CLIDiscoveredCommand:
    return command_with(
        CLICommand(
            name=long.replace("-", "_"),
            handler=HANDED_IN,
            long=long,
            short=short,
            request=request,
            help="a command under test",
            arguments=arguments,
            default=default,
        ),
        _never,
    )


def test_two_commands_cannot_claim_the_same_long_option() -> None:
    with pytest.raises(ValueError, match="'--twice'"):
        CLICommands(commands=[_command("twice"), _command("twice")])


def test_two_commands_cannot_claim_the_same_short_option() -> None:
    with pytest.raises(ValueError, match="'-x'"):
        CLICommands(commands=[_command("one", "x"), _command("other", "x")])


def test_a_short_and_a_long_option_of_the_same_letter_do_not_collide() -> None:
    commands = CLICommands(commands=[_command("x"), _command("other", "x")])
    assert commands.find("--x") is not commands.find("-x")


def test_a_command_cannot_claim_the_built_in_help_option() -> None:
    with pytest.raises(ValueError, match="'--help'"):
        CLICommands(commands=[_command("help")])


def test_a_command_cannot_claim_a_general_option() -> None:
    with pytest.raises(ValueError, match="'--log-file'"):
        CLICommands(commands=[_command("log-file")])


def test_an_option_cannot_be_declared_with_and_without_an_argument() -> None:
    with pytest.raises(ValueError, match="'--plugins'"):
        CLICommands(
            commands=[
                _command(
                    "one", request=lambda options: options.flag(CLIFlag(long="plugins", help="f"))
                ),
                _command(
                    "other",
                    request=lambda options: options.value(
                        CLIValue(long="plugins", help="v", placeholder="P", parse=str)
                    ),
                ),
            ]
        )


def test_there_is_at_most_one_default_command() -> None:
    with pytest.raises(ValueError, match="default commands"):
        CLICommands(commands=[_command("one", default=True), _command("other", default=True)])


def test_the_default_command_cannot_require_an_argument() -> None:
    with pytest.raises(ValueError, match="'one'"):
        CLICommands(commands=[_command("one", arguments=CLIArguments("HOST"), default=True)])
