#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.cli.engine.arguments import parse as cli_parse
from cmk.cli.engine.arguments import RunCommand as CLIRunCommand
from cmk.cli.engine.commands import Commands as CLICommands
from cmk.cli.engine.discovery import make_command as cli_make_command
from cmk.cli.engine.options import general_options as cli_general_options
from cmk.plugins.checkmk.cli.check import cli_command_check


def test_fake_dns_reaches_the_implicit_check() -> None:
    parsed = cli_parse(
        CLICommands(
            plugins=[cli_make_command(cli_command_check)], general_options=cli_general_options()
        ),
        ["cmk", "--fake-dns", "1.2.3.4", "myhost"],
    )

    assert isinstance(parsed, CLIRunCommand)
    assert (parsed.command.name, parsed.options, parsed.arguments) == (
        "check",
        [("--fake-dns", "1.2.3.4")],
        ["myhost"],
    )
