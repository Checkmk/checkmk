#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ruff: noqa: A005

"""Instrumentation specific to our WSGI applications"""

from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor


def instrument_app_dependencies() -> None:
    RequestsInstrumentor().instrument()
    RedisInstrumentor().instrument()
