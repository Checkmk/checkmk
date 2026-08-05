#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from base64 import b32decode
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest
from playwright.sync_api import BrowserContext, expect, Page

from cmk.crypto.totp import TOTP
from tests.system.gui.testlib.playwright.helpers import CmkCredentials
from tests.system.gui.testlib.playwright.pom.login import LoginPage
from tests.testlib.common.utils import wait_until
from tests.testlib.site import Site


def generate_code(secret: str) -> str:
    authenticator = TOTP(b32decode(secret))
    current_time = authenticator.calculate_generation(datetime.now())
    return authenticator.generate_totp(current_time)


@pytest.fixture()
def enable_two_fa(
    test_site: Site,
    new_browser_context_and_page: tuple[BrowserContext, Page],
    credentials: CmkCredentials,
) -> Iterator[tuple[CmkCredentials, str]]:
    # To avoid preexisting validate, use new_browser_context_and_page
    _, page = new_browser_context_and_page
    action_page = LoginPage(page, test_site.internal_url)
    action_page.login(credentials)

    # On two factor registration page
    action_page.main_menu.user_two_factor_authentication.click()

    # On the App Authenticator page
    action_page.main_area.check_page_title("Two-factor authentication")
    action_page.main_area.get_suggestion("Register authenticator app").click()

    # Now extract TOTP secret from text and submit
    action_page.main_area.check_page_title("Register authenticator app")
    expect(
        text_list_loc := action_page.main_area.locator("a[class='copy_to_clipboard']").locator(
            "span"
        )
    ).not_to_be_empty()

    secret = text_list_loc.all_text_contents()[0]
    otp_value = generate_code(secret)

    action_page.main_area.get_input("auth_code").fill(otp_value)
    action_page.main_area.get_suggestion("Save").click()

    expect(
        action_page.main_area.locator("div.success", has_text="Registration successful"),
        message="Authenticator app registration settings not saved",
    ).to_be_visible()

    action_page.main_menu.logout()
    try:
        yield credentials, secret
    finally:
        if test_site.file_exists(
            f"var/check_mk/web/{credentials.username}/two_factor_credentials.mk"
        ):
            test_site.delete_file(
                f"var/check_mk/web/{credentials.username}/two_factor_credentials.mk"
            )


@pytest.mark.skip(reason="CMK-37090; flake")
def test_totp_fail_login(
    test_site: Site,
    enable_two_fa: tuple[CmkCredentials, str],
    new_browser_context_and_page: tuple[BrowserContext, Page],
) -> None:
    credentials, secret = enable_two_fa
    _, page = new_browser_context_and_page
    action_page = LoginPage(page, test_site.internal_url)
    action_page.login(credentials)
    action_page.page.wait_for_url(url=re.compile("user_login_two_factor.py"), wait_until="load")

    action_page.page.get_by_role("spinbutton", name="OTP Digit 1").fill("1")
    action_page.page.get_by_role("spinbutton", name="OTP Digit 2").fill("1")
    action_page.page.get_by_role("spinbutton", name="OTP Digit 3").fill("1")
    action_page.page.get_by_role("spinbutton", name="OTP Digit 4").fill("1")
    action_page.page.get_by_role("spinbutton", name="OTP Digit 5").fill("1")
    action_page.page.get_by_role("spinbutton", name="OTP Digit 6").fill("1")

    failed_logins_file = f"var/check_mk/web/{credentials.username}/num_failed_logins.mk"

    def _validate_num_of_failed_login_mk() -> bool:
        return test_site.read_file(failed_logins_file) == "1\n"

    wait_until(
        _validate_num_of_failed_login_mk,
        timeout=60,
        interval=1,
        condition_name=f"Is '{Path(failed_logins_file).name}' updated?",
    )


@pytest.mark.skip(reason="CMK-37090; flake")
def test_totp_remove(
    test_site: Site,
    enable_two_fa: tuple[CmkCredentials, str],
    new_browser_context_and_page: tuple[BrowserContext, Page],
) -> None:
    credentials, secret = enable_two_fa
    _, page = new_browser_context_and_page
    action_page = LoginPage(page, test_site.internal_url)
    action_page.login(credentials)
    action_page.page.wait_for_url(url=re.compile("user_login_two_factor.py"), wait_until="load")
    otp_value = generate_code(secret)

    for x, i in enumerate(otp_value):
        action_page.page.get_by_role("spinbutton", name=f"OTP Digit {x + 1}").fill(i)

    action_page.page.wait_for_url(url=re.compile("index.py"), wait_until="load")
    action_page.main_menu.user_two_factor_authentication.click()
    action_page.main_area.check_page_title("Two-factor authentication")
    action_page.main_area.locator("a[title='Delete authentication via authenticator app']").click()
    action_page.main_area.locator("button:has-text('Delete')").click()

    action_page.main_menu.logout()

    action_page = LoginPage(page, test_site.internal_url)
    action_page.login(credentials)
    action_page.page.wait_for_url(url=re.compile("index.py"), wait_until="load")
