#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""some fixtures related to e2e tests and playwright"""

import logging
import os

import pytest
from playwright.sync_api import Page

from tests.testlib.playwright import PPage
from tests.testlib.site import get_site_factory, Site
from tests.testlib.version import CMKVersion


@pytest.fixture(name="test_site", scope="session", autouse=True)
def site() -> Site:
    logging.info("Setting up testsite")
    version = os.environ.get("VERSION", CMKVersion.DAILY)
    sf = get_site_factory(
        prefix="gui_e2e_", update_from_git=version == "git", install_test_python_modules=False
    )

    site_to_return = None
    if os.environ.get("REUSE", "0") == "1":
        site_to_return = sf.get_existing_site("central")
    if site_to_return is None or not site_to_return.exists():
        site_to_return = sf.get_site("central")
    logging.info("Testsite %s is up", site_to_return.id)

    return site_to_return


@pytest.fixture(name="logged_in_page")
def logged_in(test_site: Site, page: Page) -> PPage:
    username = "cmkadmin"
    password = "cmk"

    page.goto(test_site.internal_url)
    ppage = PPage(page, site_id=test_site.id)

    ppage.login(username, password)

    return ppage
