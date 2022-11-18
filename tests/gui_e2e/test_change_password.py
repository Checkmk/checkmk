#!/usr/bin/env python

# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re

import pytest

from tests.testlib.playwright import PPage
from tests.testlib.site import Site


def _change_password(page: PPage, new_pw: str, new_pw_conf: str, old_pw: str) -> None:
    # first go to dashboard to ensure we're reloading the page in case we're already there
    page.goto_main_dashboard()
    page.main_menu.user.click()
    page.main_menu.locator("text=Change password").click()
    page.main_frame.locator("input[name='cur_password']").fill(old_pw)
    page.main_frame.locator("input[name='password']").fill(new_pw)
    page.main_frame.locator("input[name='password2']").fill(new_pw_conf)
    page.main_frame.locator("#suggestions >> text=Save").click()


@pytest.mark.parametrize(
    "new_pw,new_pw_conf,old_pw",
    [
        ("new", "new", "cmk"),
        ("😎 ", "😎 ", "cmk"),
        ("😎 ", "", "cmk"),
    ],
)
def test_user_change_password_success(
    logged_in_page: PPage, new_pw: str, new_pw_conf: str, old_pw: str
) -> None:
    # Note: if these fail, we will probably also fail to reset the password to "cmk", so you might
    # have to do this manually.
    page = logged_in_page

    _change_password(page, new_pw=new_pw, new_pw_conf=new_pw_conf, old_pw=old_pw)
    page.main_frame.check_success("Successfully changed password.")

    # change the password back to cmk
    _change_password(page, new_pw="cmk", new_pw_conf="cmk", old_pw=new_pw)
    page.main_frame.check_success("Successfully changed password.")


@pytest.mark.parametrize(
    "new_pw,new_pw_conf,old_pw,expect_error_contains",
    [
        ("", "", "", "need to provide your current password"),
        ("new", "new", "", "need to provide your current password"),
        ("new", "new", "blub", "old password is wrong"),
        ("", "new", "cmk", "need to change your password"),
        ("cmk", "", "cmk", "new password must differ"),
        # Regression for Werk 14392 -- spaces are not stripped:
        ("new", "new  ", "cmk", "new passwords do not match"),
    ],
)
def test_user_change_password_errors(
    logged_in_page: PPage,
    new_pw: str,
    new_pw_conf: str,
    old_pw: str,
    expect_error_contains: str,
) -> None:
    page = logged_in_page
    _change_password(page, new_pw=new_pw, new_pw_conf=new_pw_conf, old_pw=old_pw)
    page.main_frame.check_error(re.compile(f".*{expect_error_contains}.*"))


@pytest.mark.parametrize(
    "new_pw,new_pw_conf,expect_error_contains",
    [
        ("", "new", "passwords do not match"),
        ("", "    ", "passwords do not match"),
        # Regression for Werk 14392 -- spaces are not stripped:
        ("new", "new  ", "passwords do not match"),
    ],
)
def test_edit_user_change_password_errors(
    logged_in_page: PPage,
    test_site: Site,
    new_pw: str,
    new_pw_conf: str,
    expect_error_contains: str,
) -> None:
    page = logged_in_page
    pw_field_suffix = "Y21rYWRtaW4="  # base64 'cmkadmin'
    page.page.goto(test_site.url_for_path("wato.py?edit=cmkadmin&folder=&mode=edit_user"))
    page.locator(f"input[name='_password_{pw_field_suffix}']").fill(new_pw)
    page.locator(f"input[name='_password2_{pw_field_suffix}']").fill(new_pw_conf)
    page.locator("#suggestions >> text=Save").click()
    page.check_error(re.compile(f".*{expect_error_contains}.*"))
