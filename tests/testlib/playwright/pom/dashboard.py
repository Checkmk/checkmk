#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal
from urllib.parse import urljoin, urlsplit

from playwright.sync_api import Error, expect, Locator, Page, Response
from playwright.sync_api import TimeoutError as PWTimeoutError

from tests.testlib.playwright.helpers import Keys, LocatorHelper
from tests.testlib.playwright.pom.navigation import MainArea, MainMenu, Sidebar
from tests.testlib.playwright.timeouts import TemporaryTimeout, TIMEOUT_ACTIVATE_CHANGES_MS


class PPage(LocatorHelper):
    """Playwright Page, wrapper around the page"""

    def __init__(
        self,
        page: Page,
        site_id: str,
        site_url: str | None = None,
    ) -> None:
        super().__init__(page)
        self.main_menu = MainMenu(self.page)
        self.main_area = MainArea(self.page)
        self.sidebar = Sidebar(self.page)
        self.site_id = site_id
        if site_url:
            self.site_url = site_url
        else:
            self.site_url = "".join(urlsplit(self.page.url)[0:2])
        self.username = ""
        self.password = ""

    def locator(self, selector: str = "xpath=.") -> Locator:
        return self.page.locator(selector)

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

    def activate_selected(self) -> None:
        with TemporaryTimeout(self.page, TIMEOUT_ACTIVATE_CHANGES_MS):
            self.main_area.locator("#menu_suggestion_activate_selected").click()

    def expect_success_state(self) -> None:
        expect(
            self.main_area.locator("#site_gui_e2e_central_status.msg.state_success")
        ).to_be_visible(timeout=TIMEOUT_ACTIVATE_CHANGES_MS)

        expect(
            self.main_area.locator("#site_gui_e2e_central_progress.progress.state_success")
        ).to_be_visible(timeout=TIMEOUT_ACTIVATE_CHANGES_MS)

        # assert no further changes are pending
        expect(self.main_area.locator("div.page_state.no_changes")).to_be_visible(
            timeout=TIMEOUT_ACTIVATE_CHANGES_MS
        )

    def goto_main_dashboard(self) -> None:
        """Click the banner and wait for the dashboard"""
        self.main_menu.main_page.click()
        self.main_area.check_page_title("Main dashboard")

    def select_host(self, host_name: str) -> None:
        self.main_area.locator(f"td a:has-text('{host_name}')").click()

    def goto_add_sidebar_element(self) -> None:
        self.locator("div#check_mk_sidebar >> div#add_snapin > a").click()
        self.main_area.check_page_title("Add sidebar element")

    def press_keyboard(self, key: Keys) -> None:
        self.page.keyboard.press(str(key.value))

    def go(
        self,
        url: str | None = None,
        timeout: float | None = None,
        wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] | None = None,
        referer: str | None = None,
    ) -> Response | None:
        """calls page.goto() but will accept relative urls"""
        return self.page.goto(
            urljoin(self.site_url, url), timeout=timeout, wait_until=wait_until, referer=referer
        )

    def click_and_wait(
        self,
        locator: Locator,
        navigate: bool = False,
        expected_locator: Locator | None = None,
        reload_on_error: bool = False,
        max_tries: int = 10,
    ) -> None:
        """Wait until the specified locator could be clicked.
        After a successful click, wait until the current URL has changed and is loaded
        or an expected locator is found.
        """
        url = self.page.url
        clicked = False

        for _ in range(max_tries):
            if not clicked:
                try:
                    locator.click()
                    clicked = True
                except PWTimeoutError:
                    pass

            if clicked:
                try:
                    if navigate:
                        expect(self.page).not_to_have_url(url)
                    if expected_locator:
                        expect(expected_locator).to_be_visible()
                    self.page.wait_for_load_state("networkidle")
                    return
                except AssertionError:
                    pass

            try:
                if reload_on_error:
                    self.page.reload(wait_until="networkidle")
            except Error:
                continue

        raise AssertionError(
            "Current URL did not change, expected locator not found or page failed to reload."
        )
