#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from playwright.sync_api import expect

from tests.testlib.playwright.helpers import PPage


def test_user_color_theme(logged_in_page: PPage) -> None:
    default_value = logged_in_page.main_menu.user_color_theme_button.get_attribute("value")
    logged_in_page.main_menu.user_color_theme.click()
    changed_value = logged_in_page.main_menu.user_color_theme_button.get_attribute("value")
    assert {default_value, changed_value} == {"Light", "Dark"}

    # logging out and logging in to make sure the value is saved
    logged_in_page.logout()
    logged_in_page.login()
    saved_value = logged_in_page.main_menu.user_color_theme_button.get_attribute("value")
    assert saved_value == changed_value

    logged_in_page.main_menu.user_color_theme.click()
    reverted_value = logged_in_page.main_menu.user_color_theme_button.get_attribute("value")

    assert reverted_value == default_value


def test_user_sidebar_position(logged_in_page: PPage) -> None:
    default_value = logged_in_page.main_menu.user_sidebar_position_button.get_attribute("value")
    logged_in_page.main_menu.user_sidebar_position.click()
    changed_value = logged_in_page.main_menu.user_sidebar_position_button.get_attribute("value")
    assert {default_value, changed_value} == {"Left", "Right"}

    # logging out and logging in to make sure the value is saved
    logged_in_page.logout()
    logged_in_page.login()
    saved_value = logged_in_page.main_menu.user_sidebar_position_button.get_attribute("value")
    assert saved_value == changed_value

    logged_in_page.main_menu.user_sidebar_position.click()
    reverted_value = logged_in_page.main_menu.user_sidebar_position_button.get_attribute("value")
    assert reverted_value == default_value


def test_user_edit_profile(logged_in_page: PPage) -> None:
    response = logged_in_page.go(logged_in_page.main_menu.user_edit_profile.get_attribute("href"))
    assert response and response.ok


def test_user_notification_rules(logged_in_page: PPage) -> None:
    response = logged_in_page.go(
        logged_in_page.main_menu.user_notification_rules.get_attribute("href")
    )
    assert response and response.ok


def test_user_change_password(logged_in_page: PPage) -> None:
    response = logged_in_page.go(
        logged_in_page.main_menu.user_change_password.get_attribute("href")
    )
    assert response and response.ok


def test_user_two_factor_authentication(logged_in_page: PPage) -> None:
    response = logged_in_page.go(
        logged_in_page.main_menu.user_two_factor_authentication.get_attribute("href")
    )
    assert response and response.ok


def test_user_logout(logged_in_page: PPage) -> None:
    logged_in_page.main_menu.user_logout.click()
    expect(logged_in_page.page.locator("#login_window")).to_be_visible()
