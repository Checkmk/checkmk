#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from functools import partial
from typing import Any, Literal, TypeVar

from flask import g as g
from flask import request, session
from werkzeug.local import LocalProxy

T = TypeVar("T")

VarName = Literal[
    "config",
    "display_options",
    "endpoint",
    "html",
    "output_format",
    "output_funnel",
    "permission_tracking",
    "response",
    "theme",
    "timeout_manager",
    "translation",
    "url_filter",
    "user_errors",
]

#
# RATIONALE
#
# It appears that there is a bug in Flask that prevents the application context
# from being properly copied when using `copy_current_request_context`.
#
# This bug is tracked in GitHub issue #3306 (https://github.com/pallets/flask/issues/3306),
# and it has not yet been resolved as of the latest version of Flask (1.1.5 as of this writing).
#
# Because of this, we can't store our request local variables on the `g` object, because that would
# make it impossible to have access to them from other threads whenever we would access it via
# `copy_current_request_context`.
#
# Aside:
#     There is another bug in `copy_current_request_context`, therefore use `copy_request_context`
#     in this repository. See: cmk.gui.utils.request_context:copy_request_context
#
# Because of these issues, we introduce a new meta storage dict on the Request (see cmk.gui.http)
# and store our request local variables there.
#
# NOTE:
#     The `g` object can still be used, but keep in mind that accessing those values from other
#     threads will be IMPOSSIBLE.
#


def set_global_var(name: VarName, obj: Any) -> None:
    # We ignore this, so we don't have to introduce cyclical dependencies.
    request.meta[name] = obj  # type: ignore[attr-defined]


UNBOUND_MESSAGE = """"[checkmk] Working outside of request context.

You probably tried to access a global resource (e.g. config, Theme, etc.) without being
in a request context. There are various solutions, depending on your context.

If you're operating in the GUI and try to run a thread:

    The request context is not automatically copied over whenever you spawn a thread.
    You have to do that manually by using `cmk.gui.utils.request_context:copy_request_context`

    Example:

        from cmk.gui.utils.request_context import copy_request_context

        # Bad example. Don't use threading.Thread directly. Crashes won't get propagated this way.
        thread = Thread(target=copy_request_context(target_func))
        thread.start()

    WARNING:
        Global resources which use the `g` global objects will not be accessible from newly spawned
        threads, even when using `copy_request_context`. Only resources using `set_global_var`
        will work.

        Some resources (like g.live) are intentionally left this way, due to unclear thread safety!


If you're in a script without a request context:

    Create your request context with the `script_helpers:gui_context` context manager.

"""


class Unset:
    pass


unset = Unset()


def global_var(name: VarName, default: Any | Unset = unset) -> Any:
    if default is unset:
        try:
            return request.meta[name]  # type: ignore[attr-defined]
        except RuntimeError as exc:
            raise RuntimeError(UNBOUND_MESSAGE) from exc

    return request.meta.get(name, default)  # type: ignore[attr-defined]


def session_attr(
    name: str | tuple[Literal["user"], Literal["transactions"]], type_class: type[T]
) -> T:
    def get_attr_or_item(obj, key):
        if hasattr(obj, key):
            return getattr(obj, key)

        try:
            return obj[key]
        except TypeError:
            return None

    def maybe_tuple_lookup(attr_names: tuple[str, ...]) -> T | None:
        rv = session
        for attr in attr_names:
            rv = get_attr_or_item(rv, attr)

        if rv is None:
            return None

        if not isinstance(rv, type_class):
            raise ValueError(
                f'Object session["{".".join(attr_names)}"] is not of type {type_class}'
            )

        return rv

    def maybe_str_lookup(_name: str) -> T | None:
        return getattr(session, _name)

    return LocalProxy(
        partial(maybe_tuple_lookup, name)
        if isinstance(name, tuple)
        else partial(maybe_str_lookup, name),
        unbound_message=UNBOUND_MESSAGE,
    )  # type: ignore[return-value]


# NOTE: Flask offers the proxies below, and we should go into that direction,
# too. But currently our html class is a swiss army knife with tons of
# responsibilities which we should really, really split up...


def request_local_attr(name: str, type_class: type[T]) -> T:
    """Delegate access to the corresponding attribute on RequestContext

    When the returned object is accessed, the Proxy will fetch the current
    RequestContext from the LocalStack and return the attribute given by `name`.

    Args:
        name (str): The name of the attribute on RequestContext

        type_class (type): The type of the return value. No checking is done.

    Returns:
        A proxy which wraps the value stored on RequestContext.

    """

    def maybe_str_lookup(_name: str) -> T | None:
        try:
            rv = request.meta[_name]  # type: ignore[attr-defined]
        except KeyError:
            return None
        except RuntimeError as exc:
            raise RuntimeError(UNBOUND_MESSAGE) from exc

        if rv is None:
            return rv

        if not isinstance(rv, type_class):
            raise ValueError(f'Object request.meta["{_name}"] ({rv!r}) is not of type {type_class}')

        return rv

    return LocalProxy(partial(maybe_str_lookup, name))  # type: ignore[return-value]
