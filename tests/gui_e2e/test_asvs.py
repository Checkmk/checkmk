#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""In this testing module we define tests for the
OWASP Application Security Verification Standard

Currently we aim for V4.0.3 L1

See:
- https://owasp.org/www-project-application-security-verification-standard/"""
from playwright.sync_api import BrowserContext

from tests.testlib.playwright.helpers import PPage
from tests.testlib.site import Site


def _change_password(page: PPage, old_password: str, new_password: str) -> None:
    page.main_menu.user.click()
    page.main_menu.locator("text=Change password").click()

    page.main_area.locator("input[name='_cur_password']").fill(old_password)
    page.main_area.locator("input[name='_password']").fill(new_password)
    page.main_area.locator("#suggestions >> text=Save").click()
    page.main_area.check_success("Successfully changed password.")


def test_v2_1_5(logged_in_page: PPage) -> None:
    """Verify users can change their password."""

    page = logged_in_page
    _change_password(page, "cmk", "not-cmk")
    page.logout()

    # check old password, shouldn't work anymore
    page.login("cmkadmin", "cmk")
    page.check_error("Incorrect username or password. Please try again.")

    # changing it back for other tests
    page.login("cmkadmin", "not-cmk")
    page.main_area.check_page_title("Main dashboard")
    _change_password(page, "not-cmk", "cmk")
    page.logout()

    page.login("cmkadmin", "cmk")
    page.main_area.check_page_title("Main dashboard")


def test_password_truncation_error(logged_in_page: PPage) -> None:
    """Bcrypt truncates at 72 chars, check for the error if the password is longer"""

    page = logged_in_page
    page.main_menu.user.click()
    page.main_menu.locator("text=Change password").click()

    page.main_area.locator("input[name='_cur_password']").fill("cmk")
    page.main_area.locator("input[name='_password']").fill("A" * 80)
    page.main_area.locator("#suggestions >> text=Save").click()
    page.main_area.check_error(
        "Passwords over 72 bytes would be truncated and are therefore not allowed!"
    )


def test_cookie_flags(context: BrowserContext, test_site: Site, is_chromium: bool) -> None:
    """tests for 3.4.X"""
    username = "cmkadmin"
    password = "cmk"

    page = context.new_page()
    page.goto(test_site.internal_url)
    ppage = PPage(page, site_id=test_site.id)
    ppage.login(username, password)

    cookie = context.cookies()[0]
    # V3.4.2
    assert cookie["httpOnly"]

    if is_chromium:
        # V3.4.3
        assert cookie["sameSite"] == "Lax"

    # V3.4.5
    assert cookie["path"] == "/gui_e2e_central/"
