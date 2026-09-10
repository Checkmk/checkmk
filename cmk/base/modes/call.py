#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk import trace
from cmk.base.base_app import CheckmkBaseApp
from cmk.base.modes.modes import (
    Argument,
    Arguments,
    Mode,
    NoArgument,
    OptionalArguments,
    Options,
    parse_sub_options,
    RequiredArgument,
    SubOptions,
    SubOptionsAndOptionalArguments,
    SubOptionsAndRequiredArgument,
)

tracer = trace.get_tracer()


def call(
    app: CheckmkBaseApp,
    mode: Mode,
    arg: Argument,
    all_opts: Options,
    all_args: Arguments,
    trace_context: trace.Context,
) -> int:
    sub_options = parse_sub_options(mode.sub_options, all_opts)

    with tracer.span(
        f"mode[{mode.name}]",
        attributes={
            "cmk.base.mode.name": mode.name,
            "cmk.base.mode.args": repr((arg, sub_options, all_args)),
        },
        context=trace_context,
    ):
        match mode.dispatch:
            case NoArgument(handler=handler):
                return handler(app)
            case RequiredArgument(handler=handler):
                return handler(app, arg)
            case OptionalArguments(handler=handler):
                return handler(app, all_args)
            case SubOptions(handler=handler):
                return handler(app, sub_options)
            case SubOptionsAndRequiredArgument(handler=handler):
                return handler(app, sub_options, arg)
            case SubOptionsAndOptionalArguments(handler=handler):
                return handler(app, sub_options, all_args)
