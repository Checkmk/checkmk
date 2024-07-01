#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from urllib.parse import urljoin

import pytest
from playwright.sync_api import Page

from tests.testlib.playwright.helpers import CmkCredentials
from tests.testlib.playwright.pom.login import LoginPage
from tests.testlib.site import Site


@pytest.mark.parametrize(
    ["url", "mobile_device"],
    [
        (r"index.py?start_url=%2F<SITE_ID>%2Fcheck_mk%2Fbookmark_lists.py", False),
        (r"mobile_view.py?view_name=mobile_notifications", True),
    ],
    ids=[
        "normal",
        "mobile",
    ],
)
def test_redirected_to_desired_page(
    test_site: Site, page: Page, credentials: CmkCredentials, url: str, mobile_device: bool
) -> None:
    cmk_page = url.replace(r"<SITE_ID>", test_site.id)
    visit_url = urljoin(test_site.internal_url, cmk_page)

    login_page = LoginPage(page, visit_url, mobile_device=mobile_device)
    login_page.login(credentials)
