#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re

from playwright.sync_api import expect

from tests.gui_e2e.testlib.playwright.pom.help.welcome import WelcomePage
from tests.gui_e2e.testlib.playwright.pom.monitor.dashboard import MainDashboard


def test_home_button_shows_welcome_page(dashboard_page: MainDashboard) -> None:
    """Test that clicking the home button navigates to the welcome page."""
    welcome_page = WelcomePage(dashboard_page.page, navigate_to_page=True)
    welcome_page.navigate_via_home_button()


def test_help_menu_welcome_page(dashboard_page: MainDashboard) -> None:
    """Test that clicking the Welcome page button in the Help menu shows the welcome page."""
    welcome_page = WelcomePage(dashboard_page.page, navigate_to_page=True)
    welcome_page.navigate_via_help_menu()


def test_disable_welcome_page_on_start(dashboard_page: MainDashboard) -> None:
    """Test that disabling 'Show welcome page on start' prevents showing the welcome page."""

    welcome_page = WelcomePage(dashboard_page.page, navigate_to_page=True)

    expect(
        welcome_page.show_on_start_checkbox,
        message="'Show welcome page on start' checkbox should be checked initially",
    ).to_be_checked()

    welcome_page.disable_show_on_start()

    try:
        # Click the home button and verify we don't navigate to the welcome page
        dashboard_page.main_menu.main_page.click()
        expect(
            dashboard_page.page,
            message="Should not navigate to welcome page",
        ).not_to_have_url(re.compile(r"welcome\.py"))
        expect(
            welcome_page.welcome_app,
            message="WelcomeApp should not be visible after disabling it",
        ).not_to_be_visible()
    finally:
        # Restore the setting for subsequent tests
        welcome_page.navigate_via_help_menu()
        welcome_page.enable_show_on_start()
