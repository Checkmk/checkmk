#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The deprecated "cmk --package" command."""

from collections.abc import Sequence

from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Reader as CLIReader

DEPRECATION_MSG = "This command is no longer supported. Please use `mkp%s` instead."


def _package_request(options: CLIReader) -> Sequence[str]:
    return options.arguments(CLIArguments(placeholder="COMMAND", parse=str))


cli_command_package = CLICommand(
    name="package",
    handler="cmk.plugins.checkmk.cli.handlers.package:cli_handler_package",
    long="package",
    short="P",
    request=_package_request,
    help="DEPRECATED: Do package operations",
    description=[DEPRECATION_MSG % ""],
)
