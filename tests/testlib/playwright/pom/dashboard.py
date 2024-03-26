#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal
from urllib.parse import urljoin, urlsplit

from playwright.sync_api import Page, Response

from tests.testlib.playwright.pom.navigation import CmkPage


class LoginPage(CmkPage):
    """Represents the login page of Checkmk GUI."""

    def __init__(
        self,
        page: Page,
        site_id: str,
        site_url: str | None = None,
        timeout_assertions: int | None = None,
        timeout_navigation: int | None = None,
    ) -> None:
        super().__init__(page, timeout_assertions, timeout_navigation)
        self.site_id = site_id
        if site_url:
            self.site_url = site_url
        else:
            self.site_url = "".join(urlsplit(self.page.url)[0:2])
        self.username = ""
        self.password = ""

    def login(self, username: str = "", password: str = "") -> None:
        """login to cmk"""
        if not username:
            username = self.username
        if not password:
            password = self.password
        self.page.locator("#input_user").fill(username)
        self.page.locator("#input_pass").fill(password)
        self.page.locator("#_login").click()
        self.username = username
        self.password = password

    def logout(self) -> None:
        self.main_menu.user_logout.click()

    def go(
        self,
        url: str | None = None,
        wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] | None = None,
        referer: str | None = None,
    ) -> Response | None:
        """calls page.goto() but will accept relative urls"""
        return self.page.goto(urljoin(self.site_url, url), wait_until=wait_until, referer=referer)
