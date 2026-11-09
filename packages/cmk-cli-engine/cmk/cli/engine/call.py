#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from contextlib import AbstractContextManager

from cmk.cli.engine.arguments import RunCommand
from cmk.cli.engine.commands import BoundCommand
from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode

type CommandTracer = Callable[[CLIContext, RunCommand, CLIArgs], AbstractContextManager[None]]


def call(
    context: CLIContext,
    run_command: RunCommand,
    bound: BoundCommand,
    traced: CommandTracer,
) -> CLIExitCode:
    args: CLIArgs
    match run_command.command.arguments:
        case None:
            args = ()
        case CLIArguments(optional=True):
            args = run_command.arguments
        case CLIArguments():
            args = [run_command.argument]

    with traced(context, run_command, args):
        return bound(context, args)
