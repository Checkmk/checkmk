#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Iterator
from urllib.parse import quote_plus

import pytest
from playwright.sync_api import expect

from tests.testlib.playwright.helpers import CmkCredentials
from tests.testlib.playwright.pom.change_password import ChangePassword
from tests.testlib.playwright.pom.dashboard import Dashboard
from tests.testlib.playwright.pom.login import LoginPage
from tests.testlib.playwright.pom.setup.global_settings import GlobalSettings
from tests.testlib.site import ADMIN_USER, Site


def navigate_to_edit_user_page(dashboard_page: Dashboard, user_name: str) -> None:
    dashboard_page.main_menu.setup_menu("Users").click()
    dashboard_page.page.wait_for_url(
        url=re.compile(quote_plus("wato.py?mode=users")), wait_until="load"
    )
    dashboard_page.main_area.locator(
        f"tr:has(td:has-text('{user_name}')) >> a[title='Properties']"
    ).click()
    dashboard_page.page.wait_for_url(
        url=re.compile(quote_plus(f"edit={user_name}")), wait_until="load"
    )


@pytest.fixture(name="with_password_policy")
def fixture_with_password_policy(dashboard_page: Dashboard) -> Iterator[None]:
    """Navigate to the global settings for the password policy.

    Set it to require `at least two groups` and disable the policy again when done.
    """

    def _navigate_to_password_policy() -> None:
        _setting_name = "Password policy for local accounts"
        settings_page.search_settings(_setting_name)
        settings_page.setting_link(_setting_name).click()
        dashboard_page.page.wait_for_url(
            url=re.compile(quote_plus("varname=password_policy")), wait_until="load"
        )
        expect(dashboard_page.main_area.locator(num_groups_label)).to_be_visible()

    num_groups_label = "label[for='cb_ve_p_num_groups_USE']"
    num_groups_input = "input[name='ve_p_num_groups']"
    save_btn = "#suggestions >> text=Save"

    # enable the policy
    settings_page = GlobalSettings(dashboard_page.page)
    _navigate_to_password_policy()

    dashboard_page.main_area.locator(num_groups_label).click()
    dashboard_page.main_area.locator(num_groups_input).fill("2")
    dashboard_page.main_area.locator(save_btn).click()
    _ = Dashboard(dashboard_page.page)

    yield

    # now disable
    settings_page.navigate()
    _navigate_to_password_policy()

    dashboard_page.main_area.locator(num_groups_label).click()
    dashboard_page.main_area.locator(save_btn).click()


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
    dashboard_page: Dashboard,
    new_pw: str,
    new_pw_conf: str,
) -> None:
    """Test changing the user's own password in the user profile menu"""
    # Note: if these fail, we will probably also fail to reset the password to "cmk", so you might
    # have to do this manually.

    page = dashboard_page

    change_password_page = ChangePassword(page.page)
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
    dashboard_page: Dashboard,
    new_pw: str,
    new_pw_conf: str,
    old_pw: str,
    expect_error_contains: str,
) -> None:
    """Test failure cases of changing the user's own password in the user profile menu"""
    change_password_page = ChangePassword(dashboard_page.page)
    change_password_page.change_password(old_pw, new_pw, new_pw_conf)
    change_password_page.main_area.check_error(re.compile(f".*{expect_error_contains}.*"))


def test_user_change_password_incompatible_with_policy(
    dashboard_page: Dashboard,
    with_password_policy: None,
) -> None:
    """
    Test changing the user's own password in the user profile menu to a PW that doesn't comply with
    the PW policy
    """
    change_password_page = ChangePassword(dashboard_page.page)
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
    dashboard_page: Dashboard,
    new_pw: str,
    new_pw_conf: str,
    expect_error_contains: str,
) -> None:
    """Test the password and repeat-password fields in the edit users menu"""
    page = dashboard_page
    pw_field_suffix = "Y21rYWRtaW4="  # base64 'cmkadmin'
    navigate_to_edit_user_page(page, ADMIN_USER)

    page.main_area.locator(f"input[name='_password_{pw_field_suffix}']").fill(new_pw)
    page.main_area.locator(f"input[name='_password2_{pw_field_suffix}']").fill(new_pw_conf)
    page.main_area.locator("#suggestions >> text=Save").click()
    page.main_area.check_error(re.compile(f".*{expect_error_contains}.*"))


def test_setting_password_incompatible_with_policy(
    dashboard_page: Dashboard, with_password_policy: None
) -> None:
    """
    Activate a password policy that requires at least 2 groups of characters (via fixture)
    and fail setting a password that doesn't comply with that.
    """
    pw_field_suffix = "Y21rYWRtaW4="  # base64 'cmkadmin'
    navigate_to_edit_user_page(dashboard_page, ADMIN_USER)

    dashboard_page.main_area.locator(f"input[name='_password_{pw_field_suffix}']").fill(
        "cmkcmkcmkcmk"
    )
    dashboard_page.main_area.locator(f"input[name='_password2_{pw_field_suffix}']").fill(
        "cmkcmkcmkcmk"
    )
    dashboard_page.main_area.locator("#suggestions >> text=Save").click()

    dashboard_page.main_area.check_error(
        "The password does not use enough character groups. You need to "
        "set a password which uses at least %d of them." % 2
    )
