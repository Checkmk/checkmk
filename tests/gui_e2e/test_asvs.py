#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""In this testing module we define tests for the
OWASP Application Security Verification Standard

Currently we aim for V4.0.3 L1

See:
- https://owasp.org/www-project-application-security-verification-standard/"""

from playwright.sync_api import BrowserContext, Page

from tests.gui_e2e.testlib.playwright.helpers import CmkCredentials
from tests.gui_e2e.testlib.playwright.pom.change_password import ChangePassword
from tests.gui_e2e.testlib.playwright.pom.login import LoginPage
from tests.gui_e2e.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.testlib.site import Site


def test_v2_1_5(
    test_site: Site, dashboard_page: MainDashboard, credentials: CmkCredentials
) -> None:
    """Verify users can change their password."""

    page = dashboard_page

    change_password_page = ChangePassword(dashboard_page.page)
    change_password_page.change_password(credentials.password, "not-cmk-really-not")
    change_password_page.main_area.check_success("Successfully changed password.")
    change_password_page.main_menu.logout()
    login_page = LoginPage(page.page, navigate_to_page=False)

    # check old password, shouldn't work anymore
    login_page.login(credentials)
    login_page.check_error("Incorrect username or password. Please try again.")

    # changing it back for other tests
    test_site.reset_admin_password()

    login_page.login(credentials)
    dashboard_page.navigate()
    page.check_selected_dashboard_name()


def test_password_truncation_error(dashboard_page: MainDashboard) -> None:
    """Bcrypt truncates at 72 chars, check for the error if the password is longer"""

    change_password_page = ChangePassword(dashboard_page.page)
    change_password_page.change_password("cmk", "A" * 80)
    change_password_page.main_area.check_error(
        "Passwords over 72 bytes would be truncated and are therefore not allowed!"
    )


def test_cookie_flags(
    test_site: Site,
    is_chromium: bool,
    credentials: CmkCredentials,
    new_browser_context_and_page: tuple[BrowserContext, Page],
) -> None:
    """tests for 3.4.X"""
    browser_context, page = new_browser_context_and_page
    ppage = LoginPage(page, site_url=test_site.internal_url)
    ppage.login(credentials)

    cookie = browser_context.cookies()[0]
    # V3.4.2
    assert cookie["httpOnly"]

    if is_chromium:
        # V3.4.3
        assert cookie["sameSite"] == "Lax"

    # V3.4.5
    assert cookie["path"] == f"/{test_site.id}/"
