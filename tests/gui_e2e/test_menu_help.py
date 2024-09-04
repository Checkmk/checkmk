#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re

import pytest

from tests.testlib.playwright.pom.dashboard import Dashboard
from tests.testlib.playwright.timeouts import handle_playwright_timeouterror


@pytest.mark.parametrize(
    "help_menu_button, url_pattern",
    [
        pytest.param("help_beginners_guide", "docs.checkmk.com", id="beginners_guide"),
        pytest.param("help_user_manual", "docs.checkmk.com", id="user_manual"),
        pytest.param("help_video_tutorials", "consent.youtube.com", id="video_tutorials"),
        pytest.param("help_community_forum", "forum.checkmk.com", id="community_forum"),
        pytest.param("help_plugin_api_intro", "docs.checkmk.com", id="plugin_api_intro"),
        pytest.param("help_plugin_api_docs", "/check_mk/plugin-api/", id="plugin_api_docs"),
        pytest.param("help_rest_api_intro", "docs.checkmk.com", id="rest_api_intro"),
        pytest.param("help_rest_api_docs", "/check_mk/api/doc/", id="rest_api_docs"),
        pytest.param("help_rest_api_gui", "/check_mk/api/.*/ui/", id="rest_api_gui"),
    ],
)
def test_help_menu(
    dashboard_page: Dashboard,
    help_menu_button: str,
    url_pattern: str,
) -> None:
    browser_context = dashboard_page.page.context
    pw_timeout_msg = (
        f"Expected a response to URL with pattern: `{url_pattern}`.\n"
        "None intercepted within the validation period!"
    )

    with browser_context.expect_page() as new_tab_info:
        with browser_context.expect_event(
            "response", lambda response: bool(re.findall(url_pattern, response.url))
        ) as matched_response:
            getattr(dashboard_page.main_menu, help_menu_button).click()
            with handle_playwright_timeouterror(pw_timeout_msg):
                assert matched_response.value.status in (200, 301), (
                    f"Unexpected response status code: {matched_response.value.status}, "
                    f"response url: {matched_response.value.url}"
                )
            new_page = new_tab_info.value
            new_page.wait_for_url(url=re.compile(url_pattern), wait_until="load")
            new_page.close()


def test_help_info(dashboard_page: Dashboard) -> None:
    dashboard_page.main_menu.help_info.click()
    dashboard_page.page.wait_for_url(url=re.compile("info.py$"), wait_until="load")
    dashboard_page.main_area.check_page_title("About Checkmk")
