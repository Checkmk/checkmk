#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from functools import partial
from typing import Any, Literal, TypeVar

from flask import g, session  # pylint: disable=unused-import
from typing_extensions import assert_never
from werkzeug.local import LocalProxy

T = TypeVar("T")


def set_global_var(name: str, obj: Any) -> None:
    setattr(g, name, obj)


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
            raise ValueError(f"Object g.{'.'.join(attr_names)} is not of type {type_class}")

        return rv

    def maybe_str_lookup(_name: str) -> T | None:
        return getattr(session, _name)

    if isinstance(name, tuple):  # pylint: disable=no-else-return
        return LocalProxy(partial(maybe_tuple_lookup, name))  # type: ignore
    if isinstance(name, str):
        return LocalProxy(partial(maybe_str_lookup, name))  # type: ignore

    assert_never(name)


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
            rv = getattr(g, _name)
        except AttributeError:
            return None

        if rv is None:
            return rv

        if not isinstance(rv, type_class):
            raise ValueError(f"Object g.{_name} ({rv!r}) is not of type {type_class}")

        return rv

    return LocalProxy(partial(maybe_str_lookup, name))  # type: ignore
