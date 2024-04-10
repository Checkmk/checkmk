#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import Literal, override
from urllib.parse import urljoin

from playwright.sync_api import expect, Page, Response

from tests.testlib.playwright.helpers import CmkCredentials
from tests.testlib.playwright.pom.navigation import CmkPage


class LoginPage(CmkPage):
    """Represents the login page of Checkmk GUI."""

    def __init__(
        self,
        page: Page,
        site_url: str,  # URL to one of the pages on Checkmk GUI
        timeout_assertions: int | None = None,
        timeout_navigation: int | None = None,
    ) -> None:
        self.site_url = site_url
        self._logged_in: bool = False
        super().__init__(page, timeout_assertions, timeout_navigation)

    @override
    def navigate(self) -> str:
        """Navigate to login page, like a Checkmk GUI user.

        Navigate to the `site_url` provided to `LoginPage`, which is redirected to the login page.
        Works ONLY when the user is logged out.
        Returns the URL of login page. Returns an empty-string when user is already logged in.
        """
        _url: str = ""
        if not self._logged_in:
            self.page.goto(self.site_url, wait_until="load")
            expect(self.page).to_have_url(re.compile(r"login.py"))
            self._validate_credential_elements_on_page()
            _url = self.page.url
        return _url

    def login(self, credentials: CmkCredentials) -> None:
        """Login to Checkmk GUI."""
        self.page.locator("#input_user").fill(credentials.username)
        self.page.locator("#input_pass").fill(credentials.password)
        self.page.locator("#_login").click()

    def logout(self) -> None:
        self.main_menu.user_logout.click()

    def _validate_credential_elements_on_page(self) -> None:
        expect(self.page.locator("#input_user")).to_be_visible()
        expect(self.page.locator("#input_user")).to_be_empty()
        expect(self.page.locator("#input_pass")).to_be_visible()
        expect(self.page.locator("#input_pass")).to_be_empty()

    def go(
        self,
        url: str | None = None,
        wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] | None = None,
        referer: str | None = None,
    ) -> Response | None:
        """calls page.goto() but will accept relative urls"""
        return self.page.goto(urljoin(self.site_url, url), wait_until=wait_until, referer=referer)
