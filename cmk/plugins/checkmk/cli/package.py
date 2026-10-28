#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The deprecated "cmk --package" command."""

import sys

from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Options

_DEPRECATION_MSG = "This command is no longer supported. Please use `mkp%s` instead."


def _fail_with_deprecation_msg(
    _context: CLIContext, _options: Options, argv: CLIArgs
) -> CLIExitCode:
    sys.stdout.write(_DEPRECATION_MSG % " ".join(("", *argv)) + "\n")
    return CLIExitCode.FAILURE


cli_command_package = CLICommand(
    name="package",
    long="package",
    short="P",
    handler_function=_fail_with_deprecation_msg,
    arguments=CLIArguments("COMMAND", optional=True),
    help="DEPRECATED: Do package operations",
    description=[_DEPRECATION_MSG % ""],
)
