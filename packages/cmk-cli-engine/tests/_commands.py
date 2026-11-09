#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from functools import partial

from cmk.cli.engine.commands import DiscoveredCommand as CLIDiscoveredCommand
from cmk.cli.engine.commands import inline_run as cli_inline_run
from cmk.cli.engine.discovery import make_command as cli_make_command
from cmk.cli.internal import Command as CLICommand


def inline_command[R](command: CLICommand[R]) -> CLIDiscoveredCommand:
    return cli_make_command(command, partial(cli_inline_run, command))
