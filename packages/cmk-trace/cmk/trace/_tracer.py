#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import functools
from collections.abc import Callable, Sequence

from opentelemetry import trace
from opentelemetry.context.context import Context
from opentelemetry.trace.span import Span
from opentelemetry.util import types
from opentelemetry.util._decorator import _AgnosticContextManager


class Tracer:
    def __init__(self, tracer: trace.Tracer):
        self._tracer = tracer

    def span(
        self,
        name: str,
        context: Context | None = None,
        links: Sequence[trace.Link] | None = None,
        kind: trace.SpanKind = trace.SpanKind.INTERNAL,
        attributes: types.Attributes = None,
    ) -> _AgnosticContextManager[Span]:
        return self._tracer.start_as_current_span(
            name, context=context, links=links, attributes=attributes, kind=kind
        )

    def instrument[**P, T](
        self, name: str | None = None
    ) -> Callable[[Callable[P, T]], Callable[P, T]]:
        def _instrument(func: Callable[P, T]) -> Callable[P, T]:
            span_name = name or f"{func.__module__}.{func.__name__}"
            attrs = {
                "function.name": str(func.__name__),
                "function.module": str(func.__module__),
            }

            @functools.wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                span = self._tracer.start_span(span_name, attributes=attrs)
                with trace.use_span(span, end_on_exit=True):
                    return func(*args, **kwargs)

            return wrapper

        return _instrument
