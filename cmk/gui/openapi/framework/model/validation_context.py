#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable
from typing import cast

from cmk.gui.openapi.framework._context import ApiContext


class RequestValidationContext:
    """The pydantic validation context the framework validates a request with.

    A validator reads it from `ValidationInfo.context` by declaring a second parameter of type
    `pydantic.ValidationInfo`.

    The context carries the ApiContext and nothing else: the framework is meant to be decoupled
    from watolib and the other application packages, so none of their types may appear here. A
    validator that needs a per-request application object, like the Setup folder tree, brings its
    own build function and gets the request's instance through `shared()`.
    """

    __slots__ = ("api_context", "_shared")

    def __init__(self, api_context: ApiContext) -> None:
        self.api_context = api_context
        self._shared: dict[Callable[[ApiContext], object], object] = {}

    def shared[T](self, build: Callable[[ApiContext], T]) -> T:
        """The request's instance of the value the build function creates.

        It is built on first use and shared by all validators of the request that pass the same
        function.
        """
        if build not in self._shared:
            self._shared[build] = build(self.api_context)
        return cast(T, self._shared[build])
