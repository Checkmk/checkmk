#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Attaches Python logging logs to the active span"""

import logging
from typing import override, TextIO

from opentelemetry import trace


def add_span_log_handler() -> None:
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


class _JaegerLogHandler(logging.StreamHandler[TextIO]):
    """Add python logger records to the current span"""

    @override
    def emit(self, record: logging.LogRecord) -> None:
        # See here https://docs.python.org/3/library/logging.html#logrecord-objects
        try:
            span = trace.get_current_span()
            if span is trace.INVALID_SPAN:
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
        except Exception:
            self.handleError(record)
