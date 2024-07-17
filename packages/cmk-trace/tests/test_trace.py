#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Iterator
from contextlib import contextmanager

import opentelemetry.sdk.trace as sdk_trace
import pytest
from opentelemetry import trace as otel_trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from cmk import trace


def test_exporter_from_config_disabled() -> None:
    assert (
        trace.exporter_from_config(
            trace.TraceSendConfig(enabled=False, target=trace.LocalTarget(1234)),
        )
        is None
    )


class StubExporter(OTLPSpanExporter):
    def __init__(
        self,
        endpoint: str | None = None,
        insecure: bool | None = None,
        timeout: int | None = None,
    ):
        super().__init__(
            endpoint=endpoint,
            insecure=insecure,
            credentials=None,
            headers=None,
            timeout=timeout,
            compression=None,
        )
        self.test_endpoint = endpoint
        self.test_timeout = timeout
        self.test_insecure = insecure


def test_exporter_from_config_local_site() -> None:
    config = trace.TraceSendConfig(enabled=True, target=trace.LocalTarget(1234))
    exporter = trace.exporter_from_config(config, StubExporter)
    assert isinstance(exporter, StubExporter)
    assert exporter.test_timeout == 3
    assert exporter.test_endpoint == "http://localhost:1234"
    assert exporter.test_insecure is True


@pytest.fixture(name="reset_global_fixture_provider")
def _fixture_reset_global_fixture_provider() -> Iterator[None]:
    # pylint: disable=protected-access
    provider_orig = otel_trace._TRACER_PROVIDER
    try:
        yield
    finally:
        otel_trace._TRACER_PROVIDER_SET_ONCE._done = False
        otel_trace._TRACER_PROVIDER = provider_orig


@pytest.mark.usefixtures("reset_global_fixture_provider")
def test_get_tracer_after_initialized() -> None:
    trace.init_tracing("namespace", "service")

    tracer = trace.get_tracer()
    assert isinstance(tracer, sdk_trace.Tracer)
    assert tracer.instrumentation_info.name == "cmk.trace"
    assert tracer.instrumentation_info.version == ""


@pytest.mark.usefixtures("reset_global_fixture_provider")
def test_get_tracer_verify_provider_attributes() -> None:
    trace.init_tracing("namespace", "service", "myhost")

    tracer = trace.get_tracer()
    assert isinstance(tracer, sdk_trace.Tracer)

    assert tracer.resource.attributes["service.name"] == "namespace.service"
    assert tracer.resource.attributes["service.version"] == "0.0.1"
    assert tracer.resource.attributes["service.namespace"] == "namespace"
    assert tracer.resource.attributes["host.name"] == "myhost"


@pytest.mark.usefixtures("reset_global_fixture_provider")
def test_get_current_span_without_span() -> None:
    trace.init_tracing("namespace", "service")
    assert trace.get_current_span() == otel_trace.INVALID_SPAN


@pytest.mark.usefixtures("reset_global_fixture_provider")
def test_get_current_span_with_span() -> None:
    trace.init_tracing("namespace", "service")
    with trace.get_tracer().start_as_current_span("test") as span:
        assert trace.get_current_span() == span


@pytest.mark.usefixtures("reset_global_fixture_provider")
def test_get_current_tracer_provider() -> None:
    provider = trace.init_tracing("namespace", "service")
    assert provider == trace.get_current_tracer_provider()


def test_init_logging_attaches_logs_as_events(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("cmk.trace.test")
    caplog.set_level(logging.INFO, logger="cmk.trace.test")

    with trace_logging(logger):
        trace.init_tracing("namespace", "service")
        with trace.get_tracer().start_as_current_span("test") as span:
            logger.info("HELLO")
            assert isinstance(span, sdk_trace.ReadableSpan)
            assert len(span.events) == 1
            assert span.events[0].name == "HELLO"
            assert span.events[0].attributes is not None
            assert span.events[0].attributes["log.level"] == "INFO"


@contextmanager
def trace_logging(logger: logging.Logger) -> Iterator[None]:
    orig_handlers = logger.handlers

    try:
        trace.init_logging()
        yield
    finally:
        logger.handlers = orig_handlers
