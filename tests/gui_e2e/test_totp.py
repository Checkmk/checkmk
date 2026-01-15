#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from base64 import b32decode
from datetime import datetime

from playwright.sync_api import expect

from tests.gui_e2e.testlib.playwright.helpers import CmkCredentials
from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard
from tests.gui_e2e.testlib.playwright.pom.login import LoginPage
from tests.testlib.site import Site

from cmk.crypto.totp import TOTP


def test_totp(test_site: Site, dashboard_page: Dashboard, credentials: CmkCredentials) -> None:
    # first go to dashboard to ensure we're reloading the page in case we're already there
    dashboard_page.goto_main_dashboard()

    # On two factor registration page
    dashboard_page.main_menu.user_two_factor_authentication.click()

    # On the App Authenticator page
    dashboard_page.main_area.check_page_title("Two-factor authentication")
    dashboard_page.main_area.get_suggestion("Register authenticator app").click()

    # Now extract TOTP secret from text and submit
    dashboard_page.main_area.check_page_title("Register authenticator app")
    text_list = (
        dashboard_page.main_area.locator("a[class='copy_to_clipboard']")
        .locator("span")
        .all_text_contents()
    )

    assert len(text_list) == 1

    secret = text_list[0]
    authenticator = TOTP(b32decode(secret))
    current_time = authenticator.calculate_generation(datetime.now())
    otp_value = authenticator.generate_totp(current_time)
    dashboard_page.main_area.get_input("auth_code").fill(otp_value)
    dashboard_page.main_area.get_suggestion("Save").click()

    expect(
        dashboard_page.main_area.locator("div.success").filter(has_text="Registration successful"),
        message="Authenticator app registration settings not saved",
    ).to_be_visible()

    # Log out stuff here
    dashboard_page.main_menu.logout()
    login_page = LoginPage(dashboard_page.page, navigate_to_page=False)
    login_page.login(credentials)
    expect(login_page.page).to_have_url(re.compile("user_login_two_factor.py"))

    dashboard_page.get_input("_totp_code").fill("1")
    dashboard_page.get_input("_use_totp_code").click()

    assert test_site.read_file("var/check_mk/web/cmkadmin/num_failed_logins.mk") == "1\n"

    dashboard_page.get_input("_totp_code").fill(otp_value)
    dashboard_page.get_input("_use_totp_code").click()

    # Removing the two factor mechanism
    dashboard_page.main_menu.user_two_factor_authentication.click()
    dashboard_page.main_area.check_page_title("Two-factor authentication")
    dashboard_page.main_area.locator(
        "a[title='Delete authentication via authenticator app']"
    ).click()
    dashboard_page.main_area.locator("button:has-text('Delete')").click()
