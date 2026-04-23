# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable


def map_optional[T, U](fn: Callable[[T], U], optional: T | None) -> U | None:
    """
    Map over an optional value.

    If the value is None, return None. Otherwise map the function over the value
    and return the result.

    map_optional(foo, val) == foo(val) if val is not None else None
    """
    if optional is None:
        return None
    return fn(optional)
