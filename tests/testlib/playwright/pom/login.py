#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import Literal, override
from urllib.parse import parse_qs, urljoin, urlparse

from playwright.sync_api import expect, Locator, Page, Response

from tests.testlib.playwright.helpers import CmkCredentials
from tests.testlib.playwright.pom.page import CmkPage


class LoginPage(CmkPage):
    """Represents the login page of Checkmk GUI."""

    url_suffix = r"login.py"

    def __init__(
        self,
        page: Page,
        site_url: str | None = None,  # URL to one of the pages on Checkmk GUI
        navigate_to_page: bool = True,
        mobile_device: bool = False,
        timeout_assertions: int | None = None,
        timeout_navigation: int | None = None,
    ) -> None:
        self.site_url = site_url
        self._mobile_device: bool = mobile_device
        super().__init__(page, navigate_to_page, timeout_assertions, timeout_navigation)

    def navigate(self) -> None:
        """Navigate to login page, like a Checkmk GUI user.

        Works ONLY when the user is logged out.
        Navigate to the `site_url` provided to `LoginPage`.
        `site_url` can refer to any Checkmk GUI page.
        Returns the URL of login page. Returns an empty-string when user is already logged in.
        """
        if self.site_url:
            self.page.goto(self.site_url, wait_until="load")
            self._validate_page()
        else:
            raise ValueError("No site URL provided to navigate to login page.")

    def _validate_page(self) -> None:
        """Check if the current page is the login page."""
        expect(self.page).to_have_url(re.compile(self.url_suffix))
        expect(self.username_input).to_be_visible()
        expect(self.username_input).to_be_empty()
        expect(self.password_input).to_be_visible()
        expect(self.password_input).to_be_empty()

    @property
    def username_input(self) -> Locator:
        return self.page.locator("#input_user")

    @property
    def password_input(self) -> Locator:
        return self.page.locator("#input_pass")

    @property
    def login_button(self) -> Locator:
        return self.page.locator("#_login")

    def login(self, credentials: CmkCredentials, expected_url: str | None = None) -> None:
        """Login to Checkmk GUI.

        By default, the credentials provided to `LoginPage` are used.
        """
        self.username_input.fill(credentials.username)
        self.password_input.fill(credentials.password)
        self.login_button.click()
        _url_pattern = re.escape(expected_url or self._target_page())
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")

    def _target_page(self) -> str:
        """Returns the URL of the page to be navigated after successful login.

        This URL is embedded within the login page's URL.
        """

        def _target_url_at(param: str, query: str) -> list[str]:
            queries = parse_qs(query)
            assert (
                len(queries.get(param, [])) <= 1
            ), f"Multiple instances of parameter: {param} found in {query}!"
            return queries.get(param, [])

        _url = "mobile.py" if self._mobile_device else "index.py"
        try:
            # parse target url within the query
            _url = _target_url_at("_origtarget", urlparse(self._url).query)[-1]
        except IndexError:
            # empty list: no query found
            return _url
        if self._mobile_device:
            # parse target url within the "nested" query
            _url = _target_url_at("start_url", urlparse(_url).query)[-1]
        return _url

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
