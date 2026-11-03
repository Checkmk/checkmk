#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from contextlib import AbstractContextManager

from cmk.cli.engine.commands import Argument, Arguments, Command
from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Options

type CommandTracer = Callable[[CLIContext, Command, Options, CLIArgs], AbstractContextManager[None]]


def call(
    context: CLIContext,
    command: Command,
    arg: Argument,
    sub_options: Options,
    all_args: Arguments,
    traced: CommandTracer,
) -> CLIExitCode:

    args: Arguments
    if command.argument and not command.argument_optional:
        args = [arg]
    elif command.argument:
        args = all_args
    else:
        args = ()

    with traced(context, command, sub_options, args):
        return command.handler_function(context, sub_options, args)
