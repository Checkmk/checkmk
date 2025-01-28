#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re

from playwright.sync_api import expect

from tests.gui_e2e.testlib.playwright.helpers import CmkCredentials
from tests.gui_e2e.testlib.playwright.pom.change_password import ChangePassword
from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard
from tests.gui_e2e.testlib.playwright.pom.login import LoginPage


def test_user_color_theme(dashboard_page: Dashboard, credentials: CmkCredentials) -> None:
    # Open user menu and locate `color theme button`.
    _loc = dashboard_page.main_menu.user_color_theme_button
    default_label = str(_loc.get_attribute("value"))
    default_value = str(dashboard_page.page.locator("body").get_attribute("data-theme"))
    # Click on color theme button
    _loc.click()
    # User menu closes; theme changes
    expect(_loc).not_to_have_value(default_label)
    changed_label = str(_loc.get_attribute("value"))
    changed_value = str(dashboard_page.page.locator("body").get_attribute("data-theme"))
    assert default_label != changed_label, "Changed color theme is not properly displayed!"
    assert default_value != changed_value, "Changed color theme is not properly reflected!"

    # logging out and logging in to make sure the value is saved
    dashboard_page.main_menu.logout()
    login_page = LoginPage(dashboard_page.page, navigate_to_page=False)
    login_page.login(credentials)
    saved_label = _loc.get_attribute("value")
    saved_value = str(dashboard_page.page.locator("body").get_attribute("data-theme"))
    assert saved_label == changed_label, "Saved color theme is not properly displayed!"
    assert saved_value == changed_value, "Saved color theme is not properly reflected!"

    # Open user menu and click on `color theme button`.
    dashboard_page.main_menu.user_color_theme_button.click()
    expect(_loc).not_to_have_value(saved_label)
    reverted_label = _loc.get_attribute("value")
    reverted_value = str(dashboard_page.page.locator("body").get_attribute("data-theme"))
    assert reverted_label == default_label, "Reverted color theme is not properly displayed!"
    assert reverted_value == default_value, "Reverted color theme is not properly reflected!"


def test_user_sidebar_position(dashboard_page: Dashboard, credentials: CmkCredentials) -> None:
    # Open user menu and locate `sidebar position button`.
    _loc = dashboard_page.main_menu.user_sidebar_position_button
    default_label = str(_loc.get_attribute("value"))
    default_value = str(dashboard_page.sidebar.locator().get_attribute("class"))
    # Click on sidebar position button
    _loc.click()
    # User menu closes; Sidebar position changes
    expect(_loc).not_to_have_value(default_label)
    changed_label = _loc.get_attribute("value")
    changed_value = dashboard_page.sidebar.locator().get_attribute("class")
    assert default_label != changed_label, "Changed sidebar position is not properly displayed!"
    assert default_value != changed_value, "Changed sidebar position is not properly reflected!"

    # logging out and logging in to make sure the value is saved
    dashboard_page.main_menu.logout()
    login_page = LoginPage(dashboard_page.page, navigate_to_page=False)
    login_page.login(credentials)
    saved_label = str(_loc.get_attribute("value"))
    saved_value = str(dashboard_page.sidebar.locator().get_attribute("class"))
    assert saved_label == changed_label, "Saved sidebar position is not properly displayed!"
    assert saved_value == changed_value, "Saved sidebar position is not properly reflected!"

    # Open user menu and click on `sidebar position button`.
    dashboard_page.main_menu.user_sidebar_position_button.click()
    expect(_loc).not_to_have_value(saved_label)
    reverted_label = str(_loc.get_attribute("value"))
    reverted_value = str(dashboard_page.sidebar.locator().get_attribute("class"))
    assert reverted_label == default_label, "Reverted sidebar position is not properly displayed!"
    assert reverted_value == default_value, "Reverted sidebar position is not properly reflected!"


def test_user_edit_profile(dashboard_page: Dashboard) -> None:
    dashboard_page.main_menu.user_edit_profile.click()
    dashboard_page.page.wait_for_url(url=re.compile("user_profile.py$"), wait_until="load")
    dashboard_page.main_area.check_page_title("Edit profile")


def test_user_notification_rules(dashboard_page: Dashboard) -> None:
    dashboard_page.main_menu.user_notification_rules.click()
    dashboard_page.page.wait_for_url(url=re.compile("user_notifications_p$"), wait_until="load")
    dashboard_page.main_area.check_page_title("Your personal notification rules")


def test_user_change_password(dashboard_page: Dashboard) -> None:
    dashboard_page.main_menu.user_change_password.click()
    _ = ChangePassword(dashboard_page.page, navigate_to_page=False)


def test_user_two_factor_authentication(dashboard_page: Dashboard) -> None:
    dashboard_page.main_menu.user_two_factor_authentication.click()
    dashboard_page.page.wait_for_url(
        url=re.compile("user_two_factor_overview.py$"), wait_until="load"
    )
    dashboard_page.main_area.check_page_title("Two-factor authentication")


def test_user_logout(dashboard_page: Dashboard) -> None:
    dashboard_page.main_menu.logout()
    _ = LoginPage(dashboard_page.page, navigate_to_page=False)
