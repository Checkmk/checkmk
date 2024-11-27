#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from opentelemetry import trace as otel_trace

from cmk import trace


def test_propagate_context_via_environment() -> None:
    trace.init_tracing(
        service_namespace="namespace",
        service_name="service",
        service_instance_id="instance",
        extra_resource_attributes={},
    )

    # Create span and get the environment variables for propagation
    assert trace.get_current_span() == otel_trace.INVALID_SPAN
    with trace.get_tracer().start_as_current_span("test") as orig_span:
        assert trace.get_current_span() == orig_span
        env = trace.context_for_environment()

    # Ensure the span is not active anymore
    assert trace.get_current_span() == otel_trace.INVALID_SPAN

    # Now verify extract works
    with trace.get_tracer().start_as_current_span(
        "nested", context=trace.extract_context_from_environment(env)
    ) as nested_span:
        assert nested_span.get_span_context().trace_id == orig_span.get_span_context().trace_id
