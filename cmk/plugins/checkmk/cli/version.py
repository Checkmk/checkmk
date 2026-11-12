#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The "cmk --version" command."""

from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import no_options as cli_no_options

cli_command_version = CLICommand(
    name="version",
    handler="cmk.plugins.checkmk.cli.handlers.version:cli_handler_version",
    long="version",
    short="V",
    request=cli_no_options,
    help="Print the version of Checkmk",
)
