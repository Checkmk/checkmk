#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""some fixtures related to e2e tests and playwright"""

import logging
import os
from collections.abc import Iterator

import pytest
from playwright.sync_api import BrowserContext, Page

from tests.testlib.playwright.helpers import PPage
from tests.testlib.site import get_site_factory, Site
from tests.testlib.utils import current_base_branch_name

logger = logging.getLogger(__name__)
username = "cmkadmin"
password = "cmk"


@pytest.fixture(name="test_site", scope="session", autouse=True)
def site() -> Iterator[Site]:
    logger.info("Setting up testsite")
    reuse = os.environ.get("REUSE")
    # if REUSE is undefined, a site will neither be reused nor be dropped
    reuse_site = reuse == "1"
    drop_site = reuse == "0"
    sf = get_site_factory(
        prefix="gui_e2e_",
        fallback_branch=current_base_branch_name,
    )

    site_to_return = sf.get_existing_site("central")
    if site_to_return.exists() and reuse_site:
        logger.info("Reuse existing site (REUSE=1)")
    else:
        if site_to_return.exists() and drop_site:
            logger.info("Dropping existing site (REUSE=0)")
            site_to_return.rm()
        logger.info("Creating new site")
        site_to_return = sf.get_site("central")
    logger.info("Testsite %s is up", site_to_return.id)

    try:
        yield site_to_return
    finally:
        # teardown: saving results
        # TODO: this should be unified in all suites, see CMK-11701
        site_to_return.save_results()


def log_in(log_in_url: str, page: Page, test_site: Site) -> PPage:
    page.goto(log_in_url)
    ppage = PPage(
        page,
        site_id=test_site.id,
        site_url=test_site.internal_url,
    )
    ppage.login(username, password)

    return ppage


@pytest.fixture(name="logged_in_page")
def logged_in(test_site: Site, page: Page) -> PPage:
    return log_in(test_site.internal_url, page, test_site)


@pytest.fixture(name="logged_in_page_mobile")
def logged_in_mobile(test_site: Site, context_mobile: BrowserContext) -> PPage:
    page = context_mobile.new_page()
    return log_in(test_site.internal_url_mobile, page, test_site)
