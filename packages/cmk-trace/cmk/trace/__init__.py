#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Provides functionality to enable tracing in the Python components of Checkmk"""

import socket
from collections.abc import Mapping

from opentelemetry import trace
from opentelemetry.context.context import Context as Context
from opentelemetry.sdk import trace as sdk_trace
from opentelemetry.sdk.resources import Resource

from ._config import LocalTarget as LocalTarget
from ._config import (
    service_namespace_from_config as service_namespace_from_config,
)
from ._config import trace_send_config as trace_send_config
from ._config import TraceSendConfig as TraceSendConfig
from ._propagate import (
    context_for_environment as context_for_environment,
)
from ._propagate import (
    extract_context_from_environment as extract_context_from_environment,
)
from ._tracer import Tracer

# Re-export 3rd party names to avoid direct dependencies in the code
Span = trace.Span
SpanKind = trace.SpanKind
SpanContext = trace.SpanContext
NonRecordingSpan = trace.NonRecordingSpan
Link = trace.Link
get_tracer_provider = trace.get_tracer_provider
set_span_in_context = trace.set_span_in_context
Status = trace.Status
StatusCode = trace.StatusCode
INVALID_SPAN = trace.INVALID_SPAN
ReadableSpan = sdk_trace.ReadableSpan
TracerProvider = sdk_trace.TracerProvider
get_current_span = trace.get_current_span


def init_tracing(
    *,
    service_namespace: str,
    service_name: str,
    service_instance_id: str,
    extra_resource_attributes: Mapping[str, str] | None = None,
    host_name: str | None = None,
) -> TracerProvider:
    """Create a new tracer provider and register it globally for the application run time"""
    if extra_resource_attributes is None:
        extra_resource_attributes = {}
    if host_name is None:
        host_name = socket.gethostname()
    trace.set_tracer_provider(
        provider := _init_tracer_provider(
            service_namespace,
            service_name,
            service_instance_id,
            host_name,
            extra_resource_attributes,
        )
    )
    return provider


def get_tracer(name: str | None = None) -> Tracer:
    t = trace.get_tracer(name if name else "cmk.trace")
    return Tracer(t)


def get_current_tracer_provider() -> TracerProvider:
    if isinstance(provider := trace.get_tracer_provider(), TracerProvider):
        return provider
    raise ValueError("No tracer provider found")


def _init_tracer_provider(
    service_namespace: str,
    service_name: str,
    service_instance_id: str,
    host_name: str,
    extra_resource_attributes: Mapping[str, str],
) -> TracerProvider:
    provider = TracerProvider(
        resource=Resource(
            attributes={
                "service.name": service_name,
                "service.version": "0.0.1",
                "service.namespace": service_namespace,
                "service.instance.id": service_instance_id,
                "host.name": host_name,
                **extra_resource_attributes,
            }
        )
    )
    return provider
