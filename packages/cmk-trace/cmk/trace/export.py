#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from ._config import LocalTarget, TraceSendConfig


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
