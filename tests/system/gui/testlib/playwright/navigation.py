#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from playwright.sync_api import Page

from tests.system.gui.testlib.playwright.helpers import CmkCredentials
from tests.system.gui.testlib.playwright.pom.login import LoginPage
from tests.system.gui.testlib.playwright.pom.page import CmkPage


def navigate_to_page[TCmkPage: CmkPage](
    page: Page,
    url: str,
    credentials: CmkCredentials,
    page_type: type[TCmkPage],
) -> TCmkPage:
    """Navigate to a page.

    Performs a login to Checkmk site, if necessary.
    """
    page.goto(url, wait_until="load")

    if "login.py" in page.url:
        # Log in to the site if not already logged in.
        LoginPage(page, site_url=url, navigate_to_page=False).login(credentials)

    return page_type(page, navigate_to_page=True)
