#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Final, final, Literal, NewType, override

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from cmk.agent_receiver.log import bound_contextvars

TraceID = NewType("TraceID", str)
HeaderName = Literal["b3", "x-b3-traceid", "x-trace-id", "x-request-id", "traceparent"]
# OpenTelemetry spec: all-zero trace ID is invalid
INVALID_TRACE_ID: Final[int] = 0
B3_HEADER_PRIORITY: Final[tuple[HeaderName, ...]] = ("x-b3-traceid", "x-trace-id", "x-request-id")


@final
class B3RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that extracts B3 trace headers and binds request ID to logging context.

    Follows B3 propagation specification precedence:
    https://github.com/openzipkin/b3-propagation
    """

    @override
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        trace_result = self._extract_trace_context(request)

        with bound_contextvars(request_id=trace_result.trace_id):
            response = await call_next(request)
            response.headers["x-request-id"] = trace_result.trace_id
            # Preserve original trace header per B3 spec to allow cross service tracing
            if trace_result.original_header:
                response.headers[trace_result.original_header.name] = (
                    trace_result.original_header.value
                )

            return response

    def _extract_trace_context(self, request: Request) -> _TraceExtractionResult:
        """Extract trace context following B3 precedence rules."""
        # B3 single header takes precedence (per B3 spec)
        if (
            (b3_header := request.headers.get("b3"))
            and (parts := b3_header.split("-", 1))
            and parts[0]
        ):
            return _TraceExtractionResult(
                trace_id=TraceID(parts[0]), original_header=_TraceHeader(name="b3", value=b3_header)
            )

        # Fallback to other trace headers in priority order
        for header_name in B3_HEADER_PRIORITY:
            if header_value := request.headers.get(header_name):
                return _TraceExtractionResult(
                    trace_id=TraceID(header_value),
                    original_header=_TraceHeader(name=header_name, value=header_value),
                )

        # Generate new trace ID if none found
        return _TraceExtractionResult(trace_id=_generate_otel_trace_id(), original_header=None)


@dataclass(frozen=True, slots=True)
class _TraceHeader:
    name: HeaderName
    value: str


@dataclass(frozen=True, slots=True)
class _TraceExtractionResult:
    trace_id: TraceID
    original_header: _TraceHeader | None


def _generate_otel_trace_id() -> TraceID:
    """Generate OpenTelemetry-compliant 128-bit trace ID.

    Returns:
        32-character lowercase hex string representing 16-byte trace ID.
        Guaranteed to be non-zero per OpenTelemetry specification.
    """
    trace_id_int = secrets.randbits(128)
    while trace_id_int == INVALID_TRACE_ID:
        trace_id_int = secrets.randbits(128)
    return TraceID(f"{trace_id_int:032x}")
