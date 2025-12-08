#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

from cmk import trace
from cmk.base.base_app import CheckmkBaseApp
from cmk.base.modes.modes import Mode

OptionSpec = str
Argument = str
OptionName = str
OptionFunction = Callable  # type: ignore[type-arg]
ModeFunction = Callable  # type: ignore[type-arg]
ConvertFunction = Callable  # type: ignore[type-arg]
Options = list[tuple[OptionSpec, Argument]]
Arguments = list[str]

tracer = trace.get_tracer()


def call(
    app: CheckmkBaseApp,
    mode: Mode,
    arg: Argument | None,
    all_opts: Options,
    all_args: Arguments,
    trace_context: trace.Context,
) -> int:
    sub_options = mode.get_sub_options(all_opts)

    handler_args: list[object] = [app]
    if mode.sub_options:
        handler_args.append(sub_options)

    if mode.argument and mode.argument_optional:
        handler_args.append(all_args)
    elif mode.argument:
        handler_args.append(arg)

    handler = mode.handler_function
    if handler is None:
        raise TypeError()

    with tracer.span(
        f"mode[{mode.name()}]",
        attributes={
            "cmk.base.mode.name": mode.name(),
            "cmk.base.mode.args": repr(handler_args),
        },
        context=trace_context,
    ):
        return handler(*handler_args)  # type: ignore[no-any-return]
