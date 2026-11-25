#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from typing import Final

from cmk.cli.engine.commands import DiscoveredCommand as CLIDiscoveredCommand
from cmk.cli.engine.discovery import _make_command as _cli_make_command
from cmk.cli.engine.discovery import _Run as _CLIRun
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Handler as CLIHandler
from cmk.cli.internal import Reader as CLIReader

HANDED_IN: Final = "handed.in.by:the_test"


def command_with[R](command: CLICommand[R], run: _CLIRun[R]) -> CLIDiscoveredCommand:
    return _cli_make_command(command, lambda: CLIHandler(command=command, run=run))


def command_reading(request: Callable[[CLIReader], object]) -> CLIDiscoveredCommand:
    return command_with(
        CLICommand(
            name="thing",
            handler=HANDED_IN,
            long="thing",
            request=request,
            help="Do the thing",
        ),
        lambda *_args: CLIExitCode.SUCCESS,
    )
