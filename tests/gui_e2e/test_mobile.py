#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest
from playwright.sync_api import expect

from tests.testlib.playwright.helpers import PPage

_header_selector = "div.ui-header.ui-bar-inherit.ui-header-fixed.slidedown"
_listview_selector = "ul.ui-listview.ui-listview-inset.ui-corner-all.ui-shadow"

_texts_for_selectors = [
    "Host search",
    "Service search",
    "Host problems (all)",
    "Host problems (unhandled)",
    "Service problems (all)",
    "Service problems (unhandled)",
    "History",
    "Classical web GUI",
    "Logout",
]

# "Events" appears twice as text in the homepage. Using hrefs to avoid duplications.
_hrefs_for_selectors = [
    "mobile_view.py?view_name=mobile_events",
    "mobile_view.py?view_name=ec_events_mobile",
]


def test_login(logged_in_page_mobile: PPage) -> None:
    """Login into the Chechmk mobile page and assert the presence of the header."""
    expect(
        logged_in_page_mobile.locator(_header_selector + " >> text=Checkmk Mobile")
    ).to_be_visible()


@pytest.mark.parametrize("text", _texts_for_selectors)
def test_homepage_texts(logged_in_page_mobile: PPage, text: str) -> None:
    """Assert the presence of the main locators via text selectors in the mobile homepage."""
    expect(logged_in_page_mobile.locator(_listview_selector + f" >> text={text}")).to_be_visible()


@pytest.mark.parametrize("href", _hrefs_for_selectors)
def test_homepage_hrefs(logged_in_page_mobile: PPage, href: str) -> None:
    """Assert the presence of the main locators via href selectors in the mobile homepage."""
    expect(
        logged_in_page_mobile.locator(_listview_selector + f" >> a[href='{href}']")
    ).to_be_visible()


@pytest.mark.parametrize("text", _texts_for_selectors)
def test_navigate_homepage_texts(logged_in_page_mobile: PPage, text: str) -> None:
    """Navigate all main locators via text selectors in the mobile homepage."""
    logged_in_page_mobile.locator(_listview_selector + f" >> text={text}").click()
    logged_in_page_mobile.page.go_back()


@pytest.mark.parametrize("href", _hrefs_for_selectors)
def test_navigate_homepage_hrefs(logged_in_page_mobile: PPage, href: str) -> None:
    """Navigate all main locators via href selectors in the mobile homepage."""
    logged_in_page_mobile.locator(_listview_selector + f" >> a[href='{href}']").click()
    logged_in_page_mobile.page.go_back()
