#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.cli.engine.commands import Commands as CLICommands
from cmk.cli.engine.discovery import discover_commands as cli_discover_commands
from cmk.cli.internal import Reader as CLIReader


def test_every_command_loads_its_handler() -> None:
    for command in cli_discover_commands():
        command.bind(CLIReader(lambda _declaration: ())).load()


def test_no_two_commands_claim_the_same_option() -> None:
    CLICommands(commands=cli_discover_commands())
