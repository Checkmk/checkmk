#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from collections.abc import Iterator
from urllib.parse import quote_plus

import pytest

from tests.gui_e2e.testlib.playwright.helpers import CmkCredentials
from tests.gui_e2e.testlib.playwright.pom.change_password import ChangePassword
from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard
from tests.gui_e2e.testlib.playwright.pom.login import LoginPage
from tests.gui_e2e.testlib.playwright.pom.password_policy import PasswordPolicy
from tests.testlib.site import ADMIN_USER, Site

logger = logging.getLogger(__name__)


def navigate_to_edit_user_page(dashboard_page: Dashboard, user_name: str) -> None:
    logger.info("Navigate to 'Edit user' page")
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


@pytest.fixture(name="char_groups_number_password_policy")
def set_number_of_character_groups_password_policy(
    request: pytest.FixtureRequest, dashboard_page: Dashboard
) -> Iterator[None]:
    """Set the number of character groups required in the password policy.

    Navigate to the global settings for the password policy. Set it to require
    N(parameter) character groups and disable the policy again when done.

    This fixture uses indirect pytest parametrization to define the number of character groups.
    """

    # enable the policy
    password_policy_page = PasswordPolicy(dashboard_page.page)
    password_policy_page.set_the_number_of_character_groups(request.param)

    _ = Dashboard(dashboard_page.page)

    yield

    password_policy_page.navigate()
    password_policy_page.disable_the_number_of_charachter_groups()


def change_user_password_and_check_success(
    test_site: Site, dashboard_page: Dashboard, new_password: str, confirm_new_password: str
) -> None:
    """Change user's password and check that the change was successful.

    Change the password on 'Change Password' page, check for success message,
    and login with the new password.
    """
    # Note: if these fail, we will probably also fail to reset the password to "cmk", so you might
    # have to do this manually.

    page = dashboard_page

    logger.info("Change current password and check success message")
    change_password_page = ChangePassword(page.page)
    change_password_page.change_password(
        test_site.admin_password, new_password, confirm_new_password
    )
    change_password_page.main_area.check_success("Successfully changed password.")

    logger.info("Logout and then login with the new password")
    change_password_page.main_menu.logout()
    login_page = LoginPage(page.page, navigate_to_page=False)
    new_credentials = CmkCredentials(username=ADMIN_USER, password=new_password)
    login_page.login(new_credentials)
    dashboard_page.navigate()

    # Reset the password to the original one
    test_site.reset_admin_password()


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
    """Test changing the user's own password on 'Change Password' page"""
    change_user_password_and_check_success(test_site, dashboard_page, new_pw, new_pw_conf)


@pytest.mark.parametrize(
    "char_groups_number_password_policy, password",
    [
        pytest.param("4", "012abcDEF-=#*&$@", id="4_groups-correct_password"),
    ],
    indirect=["char_groups_number_password_policy"],
)
def test_user_change_password_strict_policy_success(
    test_site: Site,
    dashboard_page: Dashboard,
    char_groups_number_password_policy: None,
    password: str,
) -> None:
    """Test user can successfully change password with a strict password policy.

    Test changing the user's own password on 'Change Password' page
    with a strict password policy (4 character groups)
    """
    change_user_password_and_check_success(test_site, dashboard_page, password, password)


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


@pytest.mark.parametrize(
    "char_groups_number_password_policy, expected_groups_number, password",
    [
        pytest.param("2", 2, "012345678910", id="2_groups-digits"),
        pytest.param("4", 4, "ABCD56789xyz", id="4_groups-uppercase_digits_lowercase"),
        pytest.param("4", 4, "012abc-=#*&$@", id="4_groups-digits_lowercase_special_chars"),
    ],
    indirect=["char_groups_number_password_policy"],
)
def test_user_change_password_incompatible_with_policy(
    dashboard_page: Dashboard,
    char_groups_number_password_policy: None,
    expected_groups_number: int,
    password: str,
) -> None:
    """
    Test changing the user's own password in the user profile menu to a PW that doesn't comply with
    the PW policy
    """
    change_password_page = ChangePassword(dashboard_page.page)
    change_password_page.change_password("cmk", password, password)
    change_password_page.main_area.check_error(
        "The password does not use enough character groups. You need to "
        "set a password which uses at least %d of them." % expected_groups_number
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

    logger.info("Change current password on 'Edit user' page")
    page.main_area.locator(f"input[name='_password_{pw_field_suffix}']").fill(new_pw)
    page.main_area.locator(f"input[name='_password2_{pw_field_suffix}']").fill(new_pw_conf)
    page.main_area.locator("#suggestions >> text=Save").click()

    page.main_area.check_error(re.compile(f".*{expect_error_contains}.*"))


@pytest.mark.parametrize(
    "char_groups_number_password_policy, expected_groups_number, password",
    [
        pytest.param("2", 2, "cmkcmkcmkcmk", id="2_groups-lowercase"),
    ],
    indirect=["char_groups_number_password_policy"],
)
def test_setting_password_incompatible_with_policy(
    dashboard_page: Dashboard,
    char_groups_number_password_policy: None,
    expected_groups_number: int,
    password: str,
) -> None:
    """
    Activate a password policy that requires at least 2 groups of characters (via fixture)
    and fail setting a password that doesn't comply with that.
    """
    pw_field_suffix = "Y21rYWRtaW4="  # base64 'cmkadmin'
    navigate_to_edit_user_page(dashboard_page, ADMIN_USER)

    logger.info("Change current password on 'Edit user' page")
    dashboard_page.main_area.locator(f"input[name='_password_{pw_field_suffix}']").fill(password)
    dashboard_page.main_area.locator(f"input[name='_password2_{pw_field_suffix}']").fill(password)
    dashboard_page.main_area.locator("#suggestions >> text=Save").click()

    dashboard_page.main_area.check_error(
        "The password does not use enough character groups. You need to "
        "set a password which uses at least %d of them." % expected_groups_number
    )
