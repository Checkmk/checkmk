#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Iterator
from contextlib import contextmanager

import opentelemetry.sdk.trace as sdk_trace
import pytest
from opentelemetry import context as otel_context
from opentelemetry import trace as otel_trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from cmk import trace
from cmk.trace import export, logs

_UNRELATED_OPTIONS = {
    "CONFIG_ADMIN_MAIL": "",
    "CONFIG_AGENT_RECEIVER": "on",
    "CONFIG_AGENT_RECEIVER_PORT": "8000",
    "CONFIG_APACHE_MODE": "own",
    "CONFIG_APACHE_TCP_ADDR": "127.0.0.1",
    "CONFIG_APACHE_TCP_PORT": "5002",
    "CONFIG_AUTOSTART": "off",
    "CONFIG_CORE": "cmc",
    "CONFIG_LIVEPROXYD": "on",
    "CONFIG_LIVESTATUS_TCP": "off",
    "CONFIG_LIVESTATUS_TCP_ONLY_FROM": "0.0.0.0 ::/0",
    "CONFIG_LIVESTATUS_TCP_PORT": "6557",
    "CONFIG_LIVESTATUS_TCP_TLS": "on",
    "CONFIG_MKEVENTD": "on",
    "CONFIG_MKEVENTD_SNMPTRAP": "off",
    "CONFIG_MKEVENTD_SYSLOG": "on",
    "CONFIG_MKEVENTD_SYSLOG_TCP": "off",
    "CONFIG_MULTISITE_AUTHORISATION": "on",
    "CONFIG_MULTISITE_COOKIE_AUTH": "on",
    "CONFIG_NSCA": "off",
    "CONFIG_NSCA_TCP_PORT": "5667",
    "CONFIG_PNP4NAGIOS": "on",
    "CONFIG_RABBITMQ_PORT": "5672",
    "CONFIG_RABBITMQ_ONLY_FROM": "0.0.0.0 ::",
    "CONFIG_TMPFS": "on",
}


def test_trace_service_namespace_from_config_not_set() -> None:
    assert (
        trace.service_namespace_from_config(
            "mysite",
            {
                **_UNRELATED_OPTIONS,
                "CONFIG_TRACE_JAEGER_ADMIN_PORT": "14269",
                "CONFIG_TRACE_JAEGER_UI_PORT": "13333",
                "CONFIG_TRACE_RECEIVE": "off",
                "CONFIG_TRACE_RECEIVE_ADDRESS": "[::1]",
                "CONFIG_TRACE_RECEIVE_PORT": "4321",
                "CONFIG_TRACE_SEND": "on",
                "CONFIG_TRACE_SEND_TARGET": "local_site",
                "CONFIG_TRACE_SERVICE_NAMESPACE": "",
            },
        )
        == "mysite"
    )


def test_trace_service_namespace_from_config_set() -> None:
    assert (
        trace.service_namespace_from_config(
            "mysite",
            {
                **_UNRELATED_OPTIONS,
                "CONFIG_TMPFS": "on",
                "CONFIG_TRACE_JAEGER_ADMIN_PORT": "14269",
                "CONFIG_TRACE_JAEGER_UI_PORT": "13333",
                "CONFIG_TRACE_RECEIVE": "off",
                "CONFIG_TRACE_RECEIVE_ADDRESS": "[::1]",
                "CONFIG_TRACE_RECEIVE_PORT": "4321",
                "CONFIG_TRACE_SEND": "on",
                "CONFIG_TRACE_SEND_TARGET": "local_site",
                "CONFIG_TRACE_SERVICE_NAMESPACE": "my.super.namespace",
            },
        )
        == "my.super.namespace"
    )


@pytest.mark.parametrize(
    "trace_enabled, expected_target", [(True, trace.LocalTarget(4321)), (False, "")]
)
def test_trace_send_config(trace_enabled: bool, expected_target: trace.LocalTarget | str) -> None:
    assert trace.trace_send_config(
        {
            **_UNRELATED_OPTIONS,
            "CONFIG_TRACE_JAEGER_ADMIN_PORT": "14269",
            "CONFIG_TRACE_JAEGER_UI_PORT": "13333",
            "CONFIG_TRACE_RECEIVE": "off",
            "CONFIG_TRACE_RECEIVE_ADDRESS": "[::1]",
            "CONFIG_TRACE_RECEIVE_PORT": "4321",
            "CONFIG_TRACE_SEND": "on" if trace_enabled else "off",
            "CONFIG_TRACE_SEND_TARGET": "local_site",
            "CONFIG_TRACE_SERVICE_NAMESPACE": "",
        }
    ) == trace.TraceSendConfig(enabled=trace_enabled, target=expected_target)


def test_exporter_from_config_disabled() -> None:
    assert (
        export.exporter_from_config(
            exporter_log_level=logging.INFO,
            config=trace.TraceSendConfig(enabled=False, target=""),
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
    exporter = export.exporter_from_config(
        exporter_log_level=logging.INFO,
        config=config,
        exporter_class=StubExporter,
    )
    assert isinstance(exporter, StubExporter)
    assert exporter.test_timeout == 3
    assert exporter.test_endpoint == "http://localhost:1234"
    assert exporter.test_insecure is True


@pytest.mark.usefixtures("reset_global_tracer_provider")
def test_get_tracer_after_initialized() -> None:
    trace.init_tracing(
        service_namespace="namespace",
        service_name="service",
        service_instance_id="instance",
    )

    tracer = trace.get_tracer()._tracer  # noqa: SLF001
    assert isinstance(tracer, sdk_trace.Tracer)
    assert tracer.instrumentation_info.name == "cmk.trace"
    assert tracer.instrumentation_info.version == ""


@pytest.mark.usefixtures("reset_global_tracer_provider")
def test_get_tracer_verify_provider_attributes() -> None:
    trace.init_tracing(
        service_namespace="namespace",
        service_name="service",
        service_instance_id="instance",
        extra_resource_attributes={"cmk.ding": "dong"},
        host_name="myhost",
    )

    tracer = trace.get_tracer()._tracer  # noqa: SLF001
    assert isinstance(tracer, sdk_trace.Tracer)

    assert tracer.resource.attributes["service.name"] == "service"
    assert tracer.resource.attributes["service.version"] == "0.0.1"
    assert tracer.resource.attributes["service.namespace"] == "namespace"
    assert tracer.resource.attributes["service.instance.id"] == "instance"
    assert tracer.resource.attributes["host.name"] == "myhost"
    assert tracer.resource.attributes["cmk.ding"] == "dong"


@pytest.mark.usefixtures("reset_global_tracer_provider")
def test_get_current_span_without_span() -> None:
    with initial_span_context():
        trace.init_tracing(
            service_namespace="namespace",
            service_name="service",
            service_instance_id="instance",
        )
        assert trace.get_current_span() == otel_trace.INVALID_SPAN


@pytest.mark.usefixtures("reset_global_tracer_provider")
def test_get_current_span_with_span() -> None:
    trace.init_tracing(
        service_namespace="namespace",
        service_name="service",
        service_instance_id="instance",
    )
    with trace.get_tracer().span("test") as span:
        assert trace.get_current_span() == span


@pytest.mark.usefixtures("reset_global_tracer_provider")
def test_get_current_tracer_provider() -> None:
    provider = trace.init_tracing(
        service_namespace="namespace",
        service_name="service",
        service_instance_id="instance",
    )
    assert provider == trace.get_current_tracer_provider()


def test_logs_initialize_attaches_logs_as_events(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("cmk.trace.test")
    caplog.set_level(logging.INFO, logger="cmk.trace.test")

    with trace_logging(logger):
        trace.init_tracing(
            service_namespace="namespace",
            service_name="service",
            service_instance_id="instance",
        )
        with trace.get_tracer().span("test") as span:
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
        logs.add_span_log_handler()
        yield
    finally:
        logger.handlers = orig_handlers


@contextmanager
def initial_span_context() -> Iterator[None]:
    token = otel_context.attach(otel_trace.set_span_in_context(otel_trace.INVALID_SPAN))
    try:
        otel_trace.set_span_in_context(otel_trace.INVALID_SPAN)
        yield
    finally:
        otel_context.detach(token)
