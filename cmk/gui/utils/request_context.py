#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import typing
from functools import update_wrapper

from flask.globals import _cv_request

RV = typing.TypeVar("RV")
P = typing.ParamSpec("P")

FuncSpec = typing.Callable[P, RV]


def copy_request_context(func: FuncSpec) -> FuncSpec:
    # RATIONALE
    #
    # This code contains stuff copied over from `copy_current_request_context`, which doesn't
    # work all the time. For more information look at its documentation. Once their version
    # gets fixed, we should replace this implementation with the Flask one.
    ctx = _cv_request.get(None)
    if ctx is None:
        raise RuntimeError(
            "'copy_request_context' can only be used when a"
            " request context is active, such as in a view function."
        )

    copied = ctx.copy()

    def wrapper(*args, **kw):
        # NOTE
        #
        # This copied context only exists during the run of the function wrapper and gets discarded
        # afterwards. This is important because `RequestContext` will check internally that its
        # entered/exited in the thread it got created in. If we use the `copied` context from
        # outside this wrapper, we would, in case we got called from a ThreadPool, be potentially
        # called from many, different threads, which would trigger a warning code in
        # `RequestContext` and the code would crash. This is slower than the other solution, but
        # whenever we run in a ThreadPool, there is no other way.
        with copied.copy():
            return copied.app.ensure_sync(func)(*args, **kw)

    return update_wrapper(wrapper, func)
