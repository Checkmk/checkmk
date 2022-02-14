#!/usr/bin/env python

# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""In this testing module we define tests for the
OWASP Application Security Verification Standard

Currently we aim for V4.0.3 L1

See:
- https://owasp.org/www-project-application-security-verification-standard/"""

from tests.testlib.playwright import PPage


def _change_password(page: PPage, old_password: str, new_password: str) -> None:
    page.main_menu.user.click()
    page.main_menu.locator("text=Change password").click()

    page.main_frame.locator("input[name='cur_password']").fill(old_password)
    page.main_frame.locator("input[name='password']").fill(new_password)
    page.main_frame.locator("#suggestions >> text=Save").click()
    page.main_frame.check_success("Successfully changed password.")


def test_v2_1_5(logged_in_page: PPage) -> None:
    """Verify users can change their password."""

    page = logged_in_page
    _change_password(page, "cmk", "not-cmk")
    page.logout()

    # check old password, shouldn't work anymore
    page.login("cmkadmin", "cmk")
    page.check_error("Invalid login")

    # changing it back for other tests
    page.login("cmkadmin", "not-cmk")
    page.main_frame.check_page_title("Main dashboard")
    _change_password(page, "not-cmk", "cmk")
    page.logout()

    page.login("cmkadmin", "cmk")
    page.main_frame.check_page_title("Main dashboard")
