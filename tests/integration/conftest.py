#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from collections.abc import Iterator

import pytest

from tests.testlib.pytest_helpers.calls import exit_pytest_on_exceptions
from tests.testlib.site import get_site_factory, Site, SiteFactory
from tests.testlib.web_session import CMKWebSession

from .event_console import CMKEventConsole

logger = logging.getLogger(__name__)


@pytest.fixture(name="site_factory", scope="session")
def _get_site_factory() -> SiteFactory:
    """Get a site factory with a prefix for test sites."""
    return get_site_factory(prefix="int_")


# Session fixtures must be in conftest.py to work properly
@pytest.fixture(name="site", scope="session")
def get_site(site_factory: SiteFactory, request: pytest.FixtureRequest) -> Iterator[Site]:
    with exit_pytest_on_exceptions(
        exit_msg=f"Failure in site creation using fixture '{__file__}::{request.fixturename}'!"
    ):
        yield from site_factory.get_test_site(
            name="test",
            auto_restart_httpd=True,
        )


@pytest.fixture(scope="session", name="web")
def fixture_web(site: Site) -> CMKWebSession:
    web = CMKWebSession(site)

    if not site.edition.is_saas_edition():
        web.login()
    site.enforce_non_localized_gui(web)
    return web


@pytest.fixture(scope="session")
def ec(site: Site) -> CMKEventConsole:
    return CMKEventConsole(site)
