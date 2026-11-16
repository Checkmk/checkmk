#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The deprecated "cmk --package" command."""

from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import no_options as cli_no_options

DEPRECATION_MSG = "This command is no longer supported. Please use `mkp%s` instead."


cli_command_package = CLICommand(
    name="package",
    handler="cmk.plugins.checkmk.cli.handlers.package:cli_handler_package",
    long="package",
    short="P",
    request=cli_no_options,
    arguments=CLIArguments(placeholder="COMMAND", parse=str),
    help="DEPRECATED: Do package operations",
    description=[DEPRECATION_MSG % ""],
)
