#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Provides functionality to enable tracing in the Python components of Checkmk"""

import logging
import socket
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Callable, TextIO

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.trace.span import INVALID_SPAN


@dataclass(frozen=True)
class LocalTarget:
    port: int


@dataclass
class TraceSendConfig:
    enabled: bool
    target: LocalTarget | str


def trace_send_config(config: Mapping[str, str]) -> TraceSendConfig:
    target: LocalTarget | str
    if (target := config.get("CONFIG_TRACE_SEND_TARGET", "local_site")) == "local_site":
        target = LocalTarget(_trace_receive_port(config))
    return TraceSendConfig(
        enabled=config.get("CONFIG_TRACE_SEND") == "on",
        target=target,
    )


def _trace_receive_port(config: Mapping[str, str]) -> int:
    return int(config["CONFIG_TRACE_RECEIVE_PORT"])


def exporter_from_config(
    config: TraceSendConfig, exporter_class: type[OTLPSpanExporter] = OTLPSpanExporter
) -> OTLPSpanExporter | None:
    if not config.enabled:
        return None
    if isinstance(config.target, LocalTarget):
        return exporter_class(
            endpoint=f"http://localhost:{config.target.port}",
            insecure=True,
            timeout=3,
        )
    return exporter_class(endpoint=config.target, timeout=3)


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


def get_current_span() -> trace.Span:
    return trace.get_current_span()


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


def init_logging() -> None:
    """Add log entries as events to spans

    We currently work with Jaeger, which does not support logs.
    Adding logs to spans is a workaround to see logs in the Jaeger UI.

    If we would switch to a different backend, we could use something like this:

        from opentelemetry._logs import set_logger_provider
        from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

        logger_provider = LoggerProvider(resource=Resource.create({"service.name": service_name}))
        set_logger_provider(logger_provider)

        exporter = OTLPLogExporter(endpoint="http://localhost:9123", insecure=True)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
        handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
        logging.getLogger().addHandler(handler)
    """
    logging.getLogger().addHandler(_JaegerLogHandler())


class _JaegerLogHandler(logging.StreamHandler[TextIO]):  # pylint: disable=too-few-public-methods
    """Add python logger records to the current span"""

    def emit(self, record: logging.LogRecord) -> None:
        # See here https://docs.python.org/3/library/logging.html#logrecord-objects
        try:
            span = trace.get_current_span()
            if span is INVALID_SPAN:
                return

            message = self.format(record)
            span.add_event(
                message,
                {
                    # "asctime": record.asctime,
                    # "created": record.created,
                    # "filename": record.filename,
                    # "funcName": record.funcName,
                    "log.level": record.levelname,
                    "log.logger": record.name,
                    # "log.message": message,
                    # "lineno": record.lineno,
                    # "module": record.module,
                    # "msecs": record.msecs,
                    # "pathname": record.pathname,
                    # "process": record.process or "",
                    # "processName": record.processName or "",
                    # "thread": record.thread or "",
                    # "threadName": record.threadName or "",
                },
            )
        except RecursionError:
            raise
        except Exception:  # pylint: disable=broad-except
            self.handleError(record)
