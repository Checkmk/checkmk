#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re

import pytest

from tests.testlib.playwright.pom.login import LoginPage


@pytest.mark.parametrize(
    "help_menu_button, url_pattern",
    [
        pytest.param(
            "help_beginners_guide",
            "docs.checkmk.com/{branch}/en/welcome.html$",
            id="beginners_guide",
        ),
        pytest.param("help_user_manual", "docs.checkmk.com/{branch}/en/$", id="user_manual"),
        pytest.param("help_video_tutorials", "consent.youtube.com", id="video_tutorials"),
        pytest.param("help_community_forum", "forum.checkmk.com/$", id="community_forum"),
        pytest.param(
            "help_plugin_api_intro",
            "docs.checkmk.com/{branch}/en/devel_intro.html$",
            id="plugin_api_intro",
        ),
        pytest.param("help_plugin_api_docs", "/check_mk/plugin-api/$", id="plugin_api_docs"),
        pytest.param(
            "help_rest_api_intro",
            "docs.checkmk.com/{branch}/en/rest_api.html$",
            id="rest_api_intro",
        ),
        pytest.param("help_rest_api_docs", "/check_mk/api/doc/$", id="rest_api_docs"),
        pytest.param("help_rest_api_gui", "/check_mk/api/1.0/ui/$", id="rest_api_gui"),
    ],
)
def test_help_menu(
    logged_in_page: LoginPage,
    help_menu_button: str,
    url_pattern: str,
    branch: str,
) -> None:

    if "{branch}" in url_pattern:
        url_pattern = url_pattern.format(branch=branch)
    browser_context = logged_in_page.page.context

    with browser_context.expect_page() as new_tab_info:
        with browser_context.expect_event(
            "response", lambda response: bool(re.findall(url_pattern, response.url))
        ) as matched_response:

            getattr(logged_in_page.main_menu, help_menu_button).click()

            assert matched_response.value.status == 200, (
                f"Unexpected response status code: {matched_response.value.status}, "
                f"response url: {matched_response.value.url}"
            )

            new_page = new_tab_info.value
            new_page.wait_for_url(url=re.compile(url_pattern), wait_until="load")
            new_page.close()


def test_help_info(logged_in_page: LoginPage) -> None:
    logged_in_page.main_menu.help_info.click()
    logged_in_page.page.wait_for_url(url=re.compile("info.py$"), wait_until="load")
    logged_in_page.main_area.check_page_title("About Checkmk")
