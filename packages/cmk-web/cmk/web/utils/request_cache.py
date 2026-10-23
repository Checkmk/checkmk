#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Values shared by the code rendering one request, each built on first use

`RequestCache` is meant to be constructed in and passed down from entry points to nested elements,
such as painters, sorters and filters of a view. Each value is named and built by a `CacheKey`.

It replaces existing approaches to caching in request globals, like `g` and `request_memoize`, with
an explicitly passed and type checked approach.

Use it for registry plugins with a fixed call signature: painters, sorters, filters, icons,
dashlets and REST endpoints. The framework level caller is not allowed to depend on feature
specific code, like cmk.gui.views on cmk.gui.wato, so the feature module defining a value defines
its key.

A cache is built from the config of its request, and a key declares the config it builds its value
from, ideally a protocol naming only what it reads. A cache hands a key only the config it was built
from, so code holding a cache of a narrowed config, like an endpoint of the REST API, reads only
the values that config can build.

A value is meant to be a read-only snapshot taken at its first use. What does not fit:

- Data the request writes and reads again, like the users or the time periods
- State passed between the parts of a request, like the painter options
- Values memoized on their arguments, like the choices of a tag group
"""

from collections.abc import Callable
from typing import cast, Final, final, override


@final
class CacheKey[C, T]:
    """Names a value of a request cache and how to build it from the config"""

    def __init__(self, name: str, factory: Callable[[C], T]) -> None:
        self._name: Final = name
        self._factory: Final = factory

    @property
    def name(self) -> str:
        return self._name

    @property
    def factory(self) -> Callable[[C], T]:
        return self._factory

    @override
    def __repr__(self) -> str:
        return f"CacheKey({self._name!r})"


@final
class RequestCache[C]:
    """The values of one request, each built on first use"""

    def __init__(self, config: C) -> None:
        self._config: Final = config
        self._values: Final[dict[object, object]] = {}

    def get[T](self, key: CacheKey[C, T]) -> T:
        if key not in self._values:
            self._values[key] = key.factory(self._config)
        return cast(T, self._values[key])
