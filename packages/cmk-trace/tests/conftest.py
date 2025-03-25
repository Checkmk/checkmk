#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest
from opentelemetry import trace as otel_trace


@pytest.fixture(name="reset_global_tracer_provider")
def _fixture_reset_global_tracer_provider() -> Iterator[None]:
    provider_orig = otel_trace._TRACER_PROVIDER  # noqa: SLF001
    try:
        yield
    finally:
        otel_trace._TRACER_PROVIDER_SET_ONCE._done = False  # noqa: SLF001
        otel_trace._TRACER_PROVIDER = provider_orig  # noqa: SLF001
