#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator

import pytest

from tests.testlib.pytest_helpers.calls import exit_pytest_on_exceptions
from tests.testlib.site import Site, SiteFactory


@pytest.fixture(name="otel_site", scope="package")
def get_site(site_factory: SiteFactory, request: pytest.FixtureRequest) -> Iterator[Site]:
    with exit_pytest_on_exceptions(
        exit_msg=f"Failure in site creation using fixture '{__file__}::{request.fixturename}'!"
    ):
        yield from site_factory.get_test_site(
            name="otel_test",
            auto_restart_httpd=True,
        )
