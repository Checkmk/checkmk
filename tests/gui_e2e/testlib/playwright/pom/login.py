#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import Literal, override
from urllib.parse import urljoin

from playwright.sync_api import expect, Locator, Page, Response

from tests.gui_e2e.testlib.playwright.helpers import CmkCredentials, DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class LoginPage(CmkPage):
    """Represents the login page of Checkmk GUI."""

    url_suffix = r"login.py"

    def __init__(
        self,
        page: Page,
        site_url: str | None = None,  # URL to one of the pages on Checkmk GUI
        navigate_to_page: bool = True,
        timeout_assertions: int | None = None,
        timeout_navigation: int | None = None,
    ) -> None:
        self.site_url = site_url
        super().__init__(
            page=page,
            navigate_to_page=navigate_to_page,
            timeout_assertions=timeout_assertions,
            timeout_navigation=timeout_navigation,
        )

    @override
    def navigate(self) -> None:
        """Navigate to login page, like a Checkmk GUI user.

        Works ONLY when the user is logged out.
        Navigate to the `site_url` provided to `LoginPage`.
        `site_url` can refer to any Checkmk GUI page.
        Returns the URL of login page. Returns an empty-string when user is already logged in.
        """
        if self.site_url:
            logger.info("Navigate to login page")
            self.page.goto(self.site_url, wait_until="load")
            self.validate_page()
        else:
            raise ValueError("No site URL provided to navigate to login page.")

    @override
    def validate_page(self) -> None:
        """Check if the current page is the login page."""
        logger.info("Validate that current page is login page")
        expect(self.page).to_have_url(re.compile(self.url_suffix))
        expect(self.username_input).to_be_visible()
        expect(self.username_input).to_be_empty()
        expect(self.password_input).to_be_visible()
        expect(self.password_input).to_be_empty()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def username_input(self) -> Locator:
        return self.page.locator("#input_user")

    @property
    def password_input(self) -> Locator:
        return self.page.locator("#input_pass")

    @property
    def login_button(self) -> Locator:
        return self.page.locator("#_login")

    def login(self, credentials: CmkCredentials) -> None:
        """Login to Checkmk GUI."""
        logger.info("Login using provided credentials")
        self.username_input.fill(credentials.username)
        self.password_input.fill(credentials.password)
        self.login_button.click()
        self.page.wait_for_load_state("load")

    @override
    def go(
        self,
        url: str | None = None,
        wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] | None = None,
        referer: str | None = None,
    ) -> Response | None:
        """calls page.goto() but will accept relative urls"""
        if self.site_url:
            return self.page.goto(
                urljoin(self.site_url, url), wait_until=wait_until, referer=referer
            )
        raise ValueError("No site URL provided")
