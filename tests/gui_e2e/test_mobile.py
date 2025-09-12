#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

import pytest
from playwright.sync_api import expect, Playwright

from tests.gui_e2e.testlib.playwright.pom.dashboard import DashboardMobile
from tests.gui_e2e.testlib.playwright.pom.login import LoginPage

_mobile_devices = ("iPhone 6", "Galaxy S8")

_header_selector = "div.ui-header.ui-bar-inherit.ui-header-fixed.slidedown"
_listview_selector = "ul.ui-listview.ui-listview-inset.ui-corner-all.ui-shadow"

_texts_for_selectors = DashboardMobile.links
_texts_for_selectors.remove("Logout")

# "Events" appears twice as text in the homepage. Using hrefs to avoid duplications.
_hrefs_for_selectors = [
    pytest.param("mobile_view.py?view_name=mobile_events", id="history-events"),
    pytest.param("mobile_view.py?view_name=ec_events_mobile", id="ec-events"),
]


@pytest.fixture(scope="module", params=_mobile_devices)
def browser_context_args(
    browser_context_args: dict[str, Any], playwright: Playwright, request: pytest.FixtureRequest
) -> dict[str, Any]:
    """Return arguments to initialize a playwright `BrowserContext` object for mobile devices.

    This overrides the `browser_context_args` fixture from gui_e2e/testlib/playwright/plugin.py.
    """
    return {
        **browser_context_args,
        **playwright.devices[str(request.param)],
    }


def test_login(dashboard_page_mobile: DashboardMobile) -> None:
    """Login into the Chechmk mobile page and assert the presence of the header."""
    expect(
        dashboard_page_mobile.locator(_header_selector + " >> text=Checkmk Mobile")
    ).to_be_visible()


@pytest.mark.parametrize("text", _texts_for_selectors)
def test_homepage_texts(dashboard_page_mobile: DashboardMobile, text: str) -> None:
    """Assert the presence of the main locators via text selectors in the mobile homepage."""
    expect(dashboard_page_mobile.locator(_listview_selector + f" >> text={text}")).to_be_visible()


@pytest.mark.parametrize("href", _hrefs_for_selectors)
def test_homepage_hrefs(dashboard_page_mobile: DashboardMobile, href: str) -> None:
    """Assert the presence of the main locators via href selectors in the mobile homepage."""
    expect(
        dashboard_page_mobile.locator(_listview_selector + f" >> a[href='{href}']")
    ).to_be_visible()


@pytest.mark.parametrize("text", _texts_for_selectors)
def test_navigate_homepage_texts(dashboard_page_mobile: DashboardMobile, text: str) -> None:
    """Navigate all main locators via text selectors in the mobile homepage."""
    dashboard_page_mobile.locator(_listview_selector + f" >> text={text}").click()
    dashboard_page_mobile.page.go_back()


@pytest.mark.parametrize("href", _hrefs_for_selectors)
def test_navigate_homepage_hrefs(dashboard_page_mobile: DashboardMobile, href: str) -> None:
    """Navigate all main locators via href selectors in the mobile homepage."""
    dashboard_page_mobile.locator(_listview_selector + f" >> a[href='{href}']").click()
    dashboard_page_mobile.page.go_back()


def test_logout(dashboard_page_mobile: DashboardMobile) -> None:
    """Logout from the GUI"""
    dashboard_page_mobile.logout.click()
    LoginPage(dashboard_page_mobile.page, navigate_to_page=False)
