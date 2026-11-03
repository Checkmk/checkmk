#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

from cmk.cli.engine.arguments import parse, RunCommand
from cmk.cli.engine.commands import Commands, general_options, make_command, parse_sub_options
from cmk.plugins.checkmk.cli.check import cli_command_check


def test_fake_dns_reaches_the_implicit_check() -> None:
    parsed = parse(
        Commands(plugins=[make_command(cli_command_check)], general_options=general_options()),
        ["cmk", "--fake-dns", "1.2.3.4", "myhost"],
    )

    assert isinstance(parsed, RunCommand)
    assert parse_sub_options(
        parsed.command.sub_options, parsed.options, logging.getLogger(__name__)
    ) == {"fake-dns": "1.2.3.4"}
