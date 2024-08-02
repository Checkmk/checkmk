#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Provides functionality to enable tracing in the Python components of Checkmk"""

import socket

from opentelemetry import trace
from opentelemetry.sdk import trace as sdk_trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import export as sdk_export

from ._config import LocalTarget as LocalTarget  # pylint: disable=useless-import-alias
from ._config import trace_send_config as trace_send_config  # pylint: disable=useless-import-alias
from ._config import TraceSendConfig as TraceSendConfig  # pylint: disable=useless-import-alias

# Re-export 3rd party names to avoid direct dependencies in the code
Span = trace.Span
SpanKind = trace.SpanKind
Link = trace.Link
get_tracer_provider = trace.get_tracer_provider
set_span_in_context = trace.set_span_in_context
Status = trace.Status
StatusCode = trace.StatusCode
INVALID_SPAN = trace.INVALID_SPAN
BatchSpanProcessor = sdk_export.BatchSpanProcessor
SpanExporter = sdk_export.SpanExporter
SpanExportResult = sdk_export.SpanExportResult
ReadableSpan = sdk_trace.ReadableSpan
TracerProvider = sdk_trace.TracerProvider
get_current_span = trace.get_current_span


def init_tracing(
    service_namespace: str, service_name: str, host_name: str | None = None
) -> TracerProvider:
    """Create a new tracer provider and register it globally for the application run time"""
    if host_name is None:
        host_name = socket.gethostname()
    trace.set_tracer_provider(
        provider := _init_tracer_provider(service_namespace, service_name, host_name)
    )
    return provider


def init_span_processor(provider: TracerProvider, exporter: SpanExporter | None = None) -> None:
    """Add a span processor to the applications tracer provider"""
    if exporter is not None:
        provider.add_span_processor(BatchSpanProcessor(exporter, export_timeout_millis=3000))


def get_tracer() -> trace.Tracer:
    return trace.get_tracer("cmk.trace")


def get_current_tracer_provider() -> TracerProvider:
    if isinstance(provider := trace.get_tracer_provider(), TracerProvider):
        return provider
    raise ValueError("No tracer provider found")


def _init_tracer_provider(
    service_namespace: str, service_name: str, host_name: str
) -> TracerProvider:
    provider = TracerProvider(
        resource=Resource(
            attributes={
                "service.name": f"{service_namespace}.{service_name}",
                "service.version": "0.0.1",
                "service.namespace": service_namespace,
                "host.name": host_name,
            }
        )
    )
    return provider
