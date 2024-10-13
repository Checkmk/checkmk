#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from opentelemetry import propagate
from opentelemetry.context.context import Context


def extract_context_from_environment(env: Mapping[str, str]) -> Context:
    """Extract and set the trace context from the environment

    The environment is expected to contain the trace context identifiers
    (TRACEPARENT + optional TRACESTATE), which is extracted and set as the
    current active context.
    """
    carrier = {k.lower(): env[k] for k in ("TRACEPARENT", "TRACESTATE") if k in env}
    return propagate.extract(carrier)


def context_for_environment() -> dict[str, str]:
    """Provide a mapping to be added to a process environment

    Sets the trace context identifiers (TRACEPARENT + optional TRACESTATE).
    The values are gathered from the current active context.
    """
    carrier: dict[str, str] = {}
    propagate.inject(carrier)
    return {k.upper(): v for k, v in carrier.items()}
