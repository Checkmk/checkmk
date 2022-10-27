#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""some fixtures related to e2e tests and playwright"""

import logging
import os

import pytest
from playwright.sync_api import Page

from tests.testlib.playwright.helpers import PPage
from tests.testlib.site import get_site_factory, Site
from tests.testlib.version import CMKVersion

logger = logging.getLogger(__name__)


@pytest.fixture(name="test_site", scope="session", autouse=True)
def site() -> Site:
    logger.info("Setting up testsite")
    version = os.environ.get("VERSION", CMKVersion.DAILY)
    reuse = os.environ.get("REUSE")
    # if REUSE is undefined, a site will neither be reused nor be dropped
    reuse_site = reuse == "1"
    drop_site = reuse == "0"
    sf = get_site_factory(
        prefix="gui_e2e_", update_from_git=version == "git", install_test_python_modules=False
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

    return site_to_return


@pytest.fixture(name="logged_in_page")
def logged_in(test_site: Site, page: Page) -> PPage:
    username = "cmkadmin"
    password = "cmk"

    page.goto(test_site.internal_url)
    ppage = PPage(
        page,
        site_id=test_site.id,
        site_url=test_site.internal_url,
    )

    ppage.login(username, password)

    return ppage
