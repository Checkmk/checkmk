#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NoReturn

import pytest

from cmk.cli.engine.commands import Commands as CLICommands
from cmk.cli.engine.commands import DiscoveredCommand as CLIDiscoveredCommand
from cmk.cli.engine.discovery import make_command as cli_make_command
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import no_options as cli_no_options


def _never(*_args: object, **_kwargs: object) -> NoReturn:
    raise AssertionError("the command must not run")


def _command(long: str, short: str | None = None) -> CLIDiscoveredCommand:
    return cli_make_command(
        CLICommand(
            name=long,
            long=long,
            short=short,
            request=cli_no_options,
            handler=_never,
            help="a command under test",
        )
    )


def test_two_commands_cannot_claim_the_same_long_option() -> None:
    with pytest.raises(ValueError, match="'twice'"):
        CLICommands(plugins=[_command("twice"), _command("twice")])


def test_two_commands_cannot_claim_the_same_short_option() -> None:
    with pytest.raises(ValueError, match="'x'"):
        CLICommands(plugins=[_command("one", "x"), _command("other", "x")])


def test_a_command_cannot_claim_the_built_in_help_option() -> None:
    with pytest.raises(ValueError, match="'help'"):
        CLICommands(plugins=[_command("help")])
