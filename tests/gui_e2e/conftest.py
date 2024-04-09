#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""some fixtures related to e2e tests and playwright"""

import logging
from collections.abc import Generator

import pytest
from playwright.sync_api import BrowserContext, Page

from tests.testlib.playwright.helpers import CmkCredentials
from tests.testlib.playwright.pom.dashboard import LoginPage
from tests.testlib.site import ADMIN_USER, get_site_factory, Site

logger = logging.getLogger(__name__)


@pytest.fixture(name="test_site", scope="session")
def get_site() -> Generator[Site, None, None]:
    yield from get_site_factory(prefix="gui_e2e_").get_test_site()


@pytest.fixture(name="credentials", scope="session")
def _credentials(test_site: Site) -> CmkCredentials:
    return CmkCredentials(username=ADMIN_USER, password=test_site.admin_password)


def log_in(log_in_url: str, page: Page, test_site: Site, credentials: CmkCredentials) -> LoginPage:
    page.goto(log_in_url)
    ppage = LoginPage(page, site_id=test_site.id, site_url=log_in_url)
    ppage.login(credentials)
    return ppage


@pytest.fixture(name="logged_in_page")
def logged_in(test_site: Site, page: Page, credentials: CmkCredentials) -> LoginPage:
    return log_in(test_site.internal_url, page, test_site, credentials)


@pytest.fixture(name="logged_in_page_mobile")
def logged_in_mobile(
    test_site: Site, context_mobile: BrowserContext, credentials: CmkCredentials
) -> LoginPage:
    page = context_mobile.new_page()
    return log_in(test_site.internal_url_mobile, page, test_site, credentials)
