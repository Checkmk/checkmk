#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    F = TypeVar("F")

    def lru_cache(maxsize: int) -> Callable[[F], F]:
        del maxsize

else:
    from functools import lru_cache

__all__ = ["regex"]


@lru_cache(maxsize=2048)
def regex(pattern: str, flags: int = 0) -> re.Pattern[str]:
    """Cache compiled regexes.

    For compatibilty, this is part of the API.
    Note that there are two other ways to achieve better performance when
    dealing with regexes using the python standard libraries :mod:`re` module.

    One option is to compile regexes using :func:`re.compile` and store them
    in a global constant.

    The other is to not explicitly compile the patterns and use the module scope
    match functions like `re.match(".*", "foobar")`.
    That way `re` will deal with memoizing.

    """
    return re.compile(pattern, flags=flags)
