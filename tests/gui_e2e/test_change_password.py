#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Iterator

import pytest

from tests.testlib.playwright.helpers import CmkCredentials
from tests.testlib.playwright.pom.change_password import ChangePassword
from tests.testlib.playwright.pom.login import LoginPage
from tests.testlib.site import ADMIN_USER, Site


@pytest.fixture(name="with_password_policy")
def fixture_with_password_policy(logged_in_page: LoginPage, test_site: Site) -> Iterator[None]:
    """
    Navigate to the global setting for the password policy, set it to require *at least two groups*
    and disable the policy again when done.
    """
    home = test_site.url_for_path("index.py")
    config_page = test_site.url_for_path(
        "wato.py?folder=&mode=edit_configvar&site=&varname=password_policy"
    )
    num_groups_label = logged_in_page.locator("label[for='cb_ve_p_num_groups_USE']")
    num_groups_input = logged_in_page.locator("input[name='ve_p_num_groups']")
    save_btn = logged_in_page.locator("#suggestions >> text=Save")

    # enable the policy
    logged_in_page.go(config_page)
    assert not num_groups_input.is_visible(), "is not already active"

    num_groups_label.click()
    num_groups_input.fill("2")
    save_btn.click()
    logged_in_page.go(home)

    yield

    # now disable
    logged_in_page.go(config_page)
    assert num_groups_input.is_visible(), "is active"

    num_groups_label.click()
    save_btn.click()
    logged_in_page.go(home)


@pytest.mark.parametrize(
    "new_pw,new_pw_conf",
    [
        ("newnewnewnew", "newnewnewnew"),
        ("😎 😎 😎 😎 😎 😎 ", "😎 😎 😎 😎 😎 😎 "),
        ("😎 😎 😎 😎 😎 😎 ", ""),
    ],
    ids=[
        "lowercase",
        "specialchars",
        "specialchars_no_confirm",
    ],
)
def test_user_change_password_success(
    test_site: Site,
    logged_in_page: LoginPage,
    new_pw: str,
    new_pw_conf: str,
) -> None:
    """Test changing the user's own password in the user profile menu"""
    # Note: if these fail, we will probably also fail to reset the password to "cmk", so you might
    # have to do this manually.

    page = logged_in_page

    change_password_page = ChangePassword(logged_in_page.page)
    change_password_page.change_password(test_site.admin_password, new_pw, new_pw_conf)
    change_password_page.main_area.check_success("Successfully changed password.")

    # Logout and then login with the new password
    change_password_page.main_menu.logout()
    login_page = LoginPage(page.page, navigate_to_page=False)
    new_credentials = CmkCredentials(username=ADMIN_USER, password=new_pw)
    login_page.login(new_credentials)
    page.main_area.check_page_title("Main dashboard")

    # Reset the password to the original one
    test_site.reset_admin_password()


@pytest.mark.parametrize(
    "new_pw, new_pw_conf, old_pw, expect_error_contains",
    [
        pytest.param("", "", "", "need to provide your current password", id="empty"),
        pytest.param("new", "new", "", "need to provide your current password", id="new-new"),
        pytest.param("new", "new", "blub", "old password is wrong", id="new-new-bulb"),
        pytest.param("", "new", "cmk", "need to change your password", id="empty-new-cmk"),
        pytest.param("cmk", "", "cmk", "new password must differ", id="cmk-empty-cmk"),
        # Regression for Werk 14392 -- spaces are not stripped:
        pytest.param("new", "new  ", "cmk", "New passwords don't match", id="new-new+spaces-cmk"),
    ],
)
def test_user_change_password_errors(
    logged_in_page: LoginPage,
    new_pw: str,
    new_pw_conf: str,
    old_pw: str,
    expect_error_contains: str,
) -> None:
    """Test failure cases of changing the user's own password in the user profile menu"""
    change_password_page = ChangePassword(logged_in_page.page)
    change_password_page.change_password(old_pw, new_pw, new_pw_conf)
    change_password_page.main_area.check_error(re.compile(f".*{expect_error_contains}.*"))


def test_user_change_password_incompatible_with_policy(
    logged_in_page: LoginPage,
    with_password_policy: None,
) -> None:
    """
    Test changing the user's own password in the user profile menu to a PW that doesn't comply with
    the PW policy
    """
    change_password_page = ChangePassword(logged_in_page.page)
    change_password_page.change_password("cmk", "123456789010", "123456789010")
    change_password_page.main_area.check_error(
        "The password does not use enough character groups. You need to "
        "set a password which uses at least %d of them." % 2
    )


@pytest.mark.parametrize(
    "new_pw, new_pw_conf, expect_error_contains",
    [
        pytest.param("", "new", "Passwords don't match", id="empty-new"),
        pytest.param("", "    ", "Passwords don't match", id="empty-spaces"),
        # Regression for Werk 14392 -- spaces are not stripped:
        pytest.param("new", "new  ", "Passwords don't match", id="new-new+spaces"),
    ],
)
def test_edit_user_change_password_errors(
    logged_in_page: LoginPage,
    test_site: Site,
    new_pw: str,
    new_pw_conf: str,
    expect_error_contains: str,
) -> None:
    """Test the password and repeat-password fields in the edit users menu"""
    page = logged_in_page
    pw_field_suffix = "Y21rYWRtaW4="  # base64 'cmkadmin'
    page.go(test_site.url_for_path("wato.py?edit=cmkadmin&folder=&mode=edit_user"))
    page.locator(f"input[name='_password_{pw_field_suffix}']").fill(new_pw)
    page.locator(f"input[name='_password2_{pw_field_suffix}']").fill(new_pw_conf)
    page.locator("#suggestions >> text=Save").click()
    page.check_error(re.compile(f".*{expect_error_contains}.*"))


def test_setting_password_incompatible_with_policy(
    logged_in_page: LoginPage, test_site: Site, with_password_policy: None
) -> None:
    """
    Activate a password policy that requries at least 2 groups of characters (via fixture)
    and fail setting a password that doesn't comply with that.
    """
    pw_field_suffix = "Y21rYWRtaW4="  # base64 'cmkadmin'
    logged_in_page.go(test_site.url_for_path("wato.py?edit=cmkadmin&folder=&mode=edit_user"))

    logged_in_page.locator(f"input[name='_password_{pw_field_suffix}']").fill("cmkcmkcmkcmk")
    logged_in_page.locator(f"input[name='_password2_{pw_field_suffix}']").fill("cmkcmkcmkcmk")
    logged_in_page.locator("#suggestions >> text=Save").click()

    logged_in_page.check_error(
        "The password does not use enough character groups. You need to "
        "set a password which uses at least %d of them." % 2
    )
