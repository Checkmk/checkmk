#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The site and the browser session the Maps end-to-end tests run against.

A suite of its own rather than more files in ``tests/system/gui``, which is a
holding area to be dissolved into feature directories (see
``tests/system/README-test-suite-organization.md``).

The browser fixtures themselves are the ones every system test gets: the
playwright plugin is registered repository-wide in ``tests/conftest.py``. What
is taken from the GUI suite is the site it is pointed at -- until those fixtures
have a shared home, one copy of them is better than a second site definition.
"""

from collections.abc import Iterator

import pytest

from tests.system.gui.conftest import navigate_to_page
from tests.system.gui.testlib.playwright.helpers import CmkCredentials
from tests.testlib.pytest_helpers.calls import exit_pytest_on_exceptions
from tests.testlib.system.site import ADMIN_USER, get_site_factory, Site, SiteFactory

__all__ = ["navigate_to_page"]


@pytest.fixture(name="site_factory", scope="session")
def fixture_site_factory() -> SiteFactory:
    return get_site_factory(prefix="maps_e2e_")


@pytest.fixture(name="test_site", scope="session")
def fixture_test_site(request: pytest.FixtureRequest, site_factory: SiteFactory) -> Iterator[Site]:
    """The Checkmk site the maps are authored and read on."""
    with exit_pytest_on_exceptions(
        exit_msg=f"Failure in site creation using fixture '{__file__}::{request.fixturename}'!"
    ):
        yield from site_factory.get_test_site(name="central")


@pytest.fixture(name="credentials", scope="session")
def fixture_credentials(test_site: Site) -> CmkCredentials:
    return CmkCredentials(username=ADMIN_USER, password=test_site.admin_password)
