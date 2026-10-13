#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk import trace
from cmk.cli.engine.commands import (
    Argument,
    Arguments,
    Command,
    Options,
    parse_sub_options,
)
from cmk.cli.internal import GlobalOptions

tracer = trace.get_tracer()


def call(
    omd_root: Path,
    command: Command,
    global_options: GlobalOptions,
    arg: Argument,
    all_opts: Options,
    all_args: Arguments,
    trace_context: trace.Context,
) -> int:
    sub_options = parse_sub_options(command.sub_options, all_opts)

    args: Arguments
    if command.argument and not command.argument_optional:
        args = [arg]
    elif command.argument:
        args = all_args
    else:
        args = ()

    with tracer.span(
        f"command[{command.name}]",
        attributes={
            "cmk.base.command.name": command.name,
            "cmk.base.command.args": repr((global_options, sub_options, args)),
        },
        context=trace_context,
    ):
        return command.handler_function(omd_root, global_options, sub_options, args)
