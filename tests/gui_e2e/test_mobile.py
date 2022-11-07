#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from playwright.sync_api import expect

from tests.testlib.playwright.helpers import PPage

_header_selector = "div.ui-header.ui-bar-inherit.ui-header-fixed.slidedown"


def test_login(logged_in_page_mobile: PPage) -> None:
    """Login into the Chechmk mobile page and assert the presence of the header."""
    expect(
        logged_in_page_mobile.locator(_header_selector + " >> text=Checkmk Mobile")
    ).to_be_visible()
