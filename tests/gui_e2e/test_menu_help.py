#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.playwright.helpers import PPage


def test_help_beginners_guide(logged_in_page: PPage) -> None:
    response = logged_in_page.go(
        logged_in_page.main_menu.help_beginners_guide.get_attribute("href")
    )
    assert response and response.ok


def test_help_user_manual(logged_in_page: PPage) -> None:
    response = logged_in_page.go(logged_in_page.main_menu.help_user_manual.get_attribute("href"))
    assert response and response.ok


def test_help_video_tutorials(logged_in_page: PPage) -> None:
    response = logged_in_page.go(
        logged_in_page.main_menu.help_video_tutorials.get_attribute("href")
    )
    assert response and response.ok


def test_help_community_forum(logged_in_page: PPage) -> None:
    response = logged_in_page.go(
        logged_in_page.main_menu.help_community_forum.get_attribute("href")
    )
    assert response and response.ok


def test_help_plugin_api_intro(logged_in_page: PPage) -> None:
    response = logged_in_page.go(
        logged_in_page.main_menu.help_plugin_api_intro.get_attribute("href")
    )
    assert response and response.ok


def test_help_plugin_api_docs(logged_in_page: PPage) -> None:
    response = logged_in_page.go(
        logged_in_page.main_menu.help_plugin_api_docs.get_attribute("href")
    )
    assert response and response.ok


def test_help_rest_api_intro(logged_in_page: PPage) -> None:
    response = logged_in_page.go(logged_in_page.main_menu.help_rest_api_intro.get_attribute("href"))
    assert response and response.ok


def test_help_rest_api_docs(logged_in_page: PPage) -> None:
    response = logged_in_page.go(logged_in_page.main_menu.help_rest_api_docs.get_attribute("href"))
    assert response and response.ok


def test_help_rest_api_gui(logged_in_page: PPage) -> None:
    response = logged_in_page.go(logged_in_page.main_menu.help_rest_api_gui.get_attribute("href"))
    assert response and response.ok


def test_help_info(logged_in_page: PPage) -> None:
    response = logged_in_page.go(logged_in_page.main_menu.help_info.get_attribute("href"))
    assert response and response.ok


def test_help_werks(logged_in_page: PPage) -> None:
    response = logged_in_page.go(logged_in_page.main_menu.help_werks.get_attribute("href"))
    assert response and response.ok
