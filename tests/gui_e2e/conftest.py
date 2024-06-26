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
from tests.testlib.playwright.pom.login import LoginPage
from tests.testlib.site import ADMIN_USER, get_site_factory, Site

logger = logging.getLogger(__name__)


@pytest.fixture(name="test_site", scope="session")
def get_site() -> Generator[Site, None, None]:
    yield from get_site_factory(prefix="gui_e2e_").get_test_site()


@pytest.fixture(name="credentials", scope="session")
def _credentials(test_site: Site) -> CmkCredentials:
    return CmkCredentials(username=ADMIN_USER, password=test_site.admin_password)


def _log_in(
    page: Page, test_site: Site, credentials: CmkCredentials, mobile_device: bool = False
) -> LoginPage:
    ppage = LoginPage(
        page,
        site_url=test_site.internal_url if not mobile_device else test_site.internal_url_mobile,
        mobile_device=mobile_device,
    )
    ppage.login(credentials)
    return ppage


@pytest.fixture(name="logged_in_page")
def logged_in(test_site: Site, page: Page, credentials: CmkCredentials) -> LoginPage:
    return _log_in(page, test_site, credentials)


@pytest.fixture(name="logged_in_page_mobile")
def logged_in_mobile(
    test_site: Site, context_mobile: BrowserContext, credentials: CmkCredentials
) -> LoginPage:
    page = context_mobile.new_page()
    return _log_in(page, test_site, credentials, mobile_device=True)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-rules",
        action="store_true",
        default=False,
        help="Store updated rule output as static references: rules already stored as reference"
        "are updated and new ones are added.",
    )


@pytest.fixture(name="branch", scope="session")
def current_branch(test_site: Site) -> str:
    if test_site.version.branch_version == "2.4.0":
        branch = "master"
    elif test_site.version.branch_version == "2.3.0":
        branch = "latest"
    else:
        raise ValueError(f"Unsupported branch version: {test_site.version.branch_version}")
    return branch
