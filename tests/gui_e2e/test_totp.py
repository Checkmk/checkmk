#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from base64 import b32decode
from datetime import datetime

from tests.testlib.playwright.helpers import CmkCredentials
from tests.testlib.playwright.pom.login import LoginPage
from tests.testlib.site import Site

from cmk.utils.totp import TOTP


def test_totp(test_site: Site, logged_in_page: LoginPage, credentials: CmkCredentials) -> None:
    # first go to dashboard to ensure we're reloading the page in case we're already there
    logged_in_page.goto_main_dashboard()

    # On two factor registration page
    logged_in_page.main_menu.user_two_factor_authentication.click()

    # On the App Authenticator page
    logged_in_page.main_area.check_page_title("Two-factor authentication")
    logged_in_page.main_area.get_suggestion("Register authenticator app").click()

    # Now extract TOTP secret from text and submit
    logged_in_page.main_area.check_page_title("Register authenticator app")
    text_list = (
        logged_in_page.main_area.locator("a[class='copy_to_clipboard']")
        .locator("span")
        .all_text_contents()
    )

    assert len(text_list) == 1

    secret = text_list[0]
    authenticator = TOTP(b32decode(secret))
    current_time = authenticator.calculate_generation(datetime.now())
    otp_value = authenticator.generate_totp(current_time)
    logged_in_page.main_area.get_input("auth_code").fill(otp_value)
    logged_in_page.main_area.get_suggestion("Save").click()

    # Log out stuff here
    logged_in_page.logout()
    logged_in_page.login(credentials, "user_login_two_factor.py")
    logged_in_page.get_input("_totp_code").fill("1")
    logged_in_page.get_input("_use_totp_code").click()

    assert test_site.read_file("var/check_mk/web/cmkadmin/num_failed_logins.mk") == "1\n"

    logged_in_page.get_input("_totp_code").fill(otp_value)
    logged_in_page.get_input("_use_totp_code").click()

    # Removing the two factor mechanism
    logged_in_page.main_menu.user_two_factor_authentication.click()
    logged_in_page.main_area.check_page_title("Two-factor authentication")
    logged_in_page.main_area.locator(
        "a[title='Delete authentication via authenticator app']"
    ).click()
    logged_in_page.main_area.locator("button:has-text('Delete')").click()
