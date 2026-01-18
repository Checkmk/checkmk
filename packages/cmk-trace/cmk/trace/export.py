#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import opentelemetry.exporter.otlp.proto.grpc.exporter as grpc_exporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import export as sdk_export
from opentelemetry.sdk.trace import TracerProvider

from ._config import LocalTarget, TraceSendConfig

# Re-export 3rd party names to avoid direct dependencies in the code
BatchSpanProcessor = sdk_export.BatchSpanProcessor
SpanExporter = sdk_export.SpanExporter
SpanExportResult = sdk_export.SpanExportResult


def exporter_from_config(
    exporter_log_level: int,
    config: TraceSendConfig,
    exporter_class: type[OTLPSpanExporter] = OTLPSpanExporter,
) -> OTLPSpanExporter | None:
    if not config.enabled:
        return None

    _set_exporter_logging(exporter_log_level)

    if isinstance(config.target, LocalTarget):
        return exporter_class(
            endpoint=f"http://localhost:{config.target.port}",
            insecure=True,
            timeout=3,
        )
    return exporter_class(endpoint=config.target, timeout=3)


def init_span_processor(provider: TracerProvider, exporter: SpanExporter | None = None) -> None:
    """Add a span processor to the applications tracer provider"""
    if exporter is not None:
        provider.add_span_processor(BatchSpanProcessor(exporter, export_timeout_millis=3000))


def _set_exporter_logging(level: int) -> None:
    """Set the log level of the OTLP exporter

    Set to logging.ERROR or higher to suppress messages like this:

    `Transient error StatusCode.UNAVAILABLE encountered while exporting traces to localhost:4321,
    retrying in 1s.`

    Set to logging.CRITICAL to suppress error messages like

    `Failed to export traces to localhost:4418, error code: StatusCode.UNAVAILABLE`
    """
    logging.getLogger(grpc_exporter.__name__).setLevel(level)
