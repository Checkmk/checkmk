#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk import trace
from cmk.base.base_app import CheckmkBaseApp
from cmk.cli.engine.modes import (
    Argument,
    Arguments,
    Mode,
    Options,
    parse_sub_options,
)
from cmk.cli.internal import GlobalOptions

tracer = trace.get_tracer()


def call(
    app: CheckmkBaseApp,
    mode: Mode,
    global_options: GlobalOptions,
    arg: Argument,
    all_opts: Options,
    all_args: Arguments,
    trace_context: trace.Context,
) -> int:
    sub_options = parse_sub_options(mode.sub_options, all_opts)

    args: Arguments
    if mode.argument and not mode.argument_optional:
        args = [arg]
    elif mode.argument:
        args = all_args
    else:
        args = ()

    with tracer.span(
        f"mode[{mode.name}]",
        attributes={
            "cmk.base.mode.name": mode.name,
            "cmk.base.mode.args": repr((global_options, sub_options, args)),
        },
        context=trace_context,
    ):
        return mode.handler_function(app, global_options, sub_options, args)
