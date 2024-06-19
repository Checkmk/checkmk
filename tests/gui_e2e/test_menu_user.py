#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from playwright.sync_api import expect

from tests.testlib.playwright.helpers import CmkCredentials
from tests.testlib.playwright.pom.login import LoginPage


def test_user_color_theme(logged_in_page: LoginPage, credentials: CmkCredentials) -> None:
    # Open user menu and locate `color theme button`.
    _loc = logged_in_page.main_menu.user_color_theme_button
    default_label = str(_loc.get_attribute("value"))
    default_value = str(logged_in_page.page.locator("body").get_attribute("data-theme"))
    # Click on color theme button
    _loc.click()
    # User menu closes; theme changes
    expect(_loc).not_to_have_value(default_label)
    changed_label = str(_loc.get_attribute("value"))
    changed_value = str(logged_in_page.page.locator("body").get_attribute("data-theme"))
    assert default_label != changed_label, "Changed color theme is not properly displayed!"
    assert default_value != changed_value, "Changed color theme is not properly reflected!"

    # logging out and logging in to make sure the value is saved
    logged_in_page.logout()
    logged_in_page.login(credentials)
    saved_label = _loc.get_attribute("value")
    saved_value = str(logged_in_page.page.locator("body").get_attribute("data-theme"))
    assert saved_label == changed_label, "Saved color theme is not properly displayed!"
    assert saved_value == changed_value, "Saved color theme is not properly reflected!"

    # Open user menu and click on `color theme button`.
    logged_in_page.main_menu.user_color_theme_button.click()
    expect(_loc).not_to_have_value(saved_label)
    reverted_label = _loc.get_attribute("value")
    reverted_value = str(logged_in_page.page.locator("body").get_attribute("data-theme"))
    assert reverted_label == default_label, "Reverted color theme is not properly displayed!"
    assert reverted_value == default_value, "Reverted color theme is not properly reflected!"


def test_user_sidebar_position(logged_in_page: LoginPage, credentials: CmkCredentials) -> None:
    # Open user menu and locate `sidebar position button`.
    _loc = logged_in_page.main_menu.user_sidebar_position_button
    default_label = str(_loc.get_attribute("value"))
    default_value = str(logged_in_page.sidebar.locator().get_attribute("class"))
    # Click on sidebar position button
    _loc.click()
    # User menu closes; Sidebar position changes
    expect(_loc).not_to_have_value(default_label)
    changed_label = _loc.get_attribute("value")
    changed_value = logged_in_page.sidebar.locator().get_attribute("class")
    assert default_label != changed_label, "Changed sidebar position is not properly displayed!"
    assert default_value != changed_value, "Changed sidebar position is not properly reflected!"

    # logging out and logging in to make sure the value is saved
    logged_in_page.logout()
    logged_in_page.login(credentials)
    saved_label = str(_loc.get_attribute("value"))
    saved_value = str(logged_in_page.sidebar.locator().get_attribute("class"))
    assert saved_label == changed_label, "Saved sidebar position is not properly displayed!"
    assert saved_value == changed_value, "Saved sidebar position is not properly reflected!"

    # Open user menu and click on `sidebar position button`.
    logged_in_page.main_menu.user_sidebar_position_button.click()
    expect(_loc).not_to_have_value(saved_label)
    reverted_label = str(_loc.get_attribute("value"))
    reverted_value = str(logged_in_page.sidebar.locator().get_attribute("class"))
    assert reverted_label == default_label, "Reverted sidebar position is not properly displayed!"
    assert reverted_value == default_value, "Reverted sidebar position is not properly reflected!"


def test_user_edit_profile(logged_in_page: LoginPage) -> None:
    response = logged_in_page.go(logged_in_page.main_menu.user_edit_profile.get_attribute("href"))
    assert response and response.ok


def test_user_notification_rules(logged_in_page: LoginPage) -> None:
    response = logged_in_page.go(
        logged_in_page.main_menu.user_notification_rules.get_attribute("href")
    )
    assert response and response.ok


def test_user_change_password(logged_in_page: LoginPage) -> None:
    response = logged_in_page.go(
        logged_in_page.main_menu.user_change_password.get_attribute("href")
    )
    assert response and response.ok


def test_user_two_factor_authentication(logged_in_page: LoginPage) -> None:
    response = logged_in_page.go(
        logged_in_page.main_menu.user_two_factor_authentication.get_attribute("href")
    )
    assert response and response.ok


def test_user_logout(logged_in_page: LoginPage) -> None:
    logged_in_page.main_menu.user_logout.click()
    expect(logged_in_page.page.locator("#login_window")).to_be_visible()
