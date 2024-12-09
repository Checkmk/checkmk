#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
from collections.abc import Iterator

import pytest
from opentelemetry.instrumentation.requests import RequestsInstrumentor

from tests.testlib.site import (
    get_site_factory,
    Site,
    tracing_config_from_env,
)

site_factory = get_site_factory(prefix="comp_")

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session", autouse=True)
def instrument_requests() -> None:
    RequestsInstrumentor().instrument()


@pytest.fixture(scope="session")
def site(request: pytest.FixtureRequest) -> Iterator[Site]:
    with site_factory.get_test_site_ctx(
        "central",
        description=request.node.name,
        auto_restart_httpd=True,
        tracing_config=tracing_config_from_env(os.environ),
    ) as this_site:
        yield this_site
