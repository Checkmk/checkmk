#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from dataclasses import dataclass
from typing import Iterator

import pytest
from playwright.sync_api import Page, Request, Route

from tests.testlib.playwright.pom.dashboard import Dashboard
from tests.testlib.playwright.timeouts import handle_playwright_timeouterror
from tests.testlib.pytest_helpers.marks import skip_if_not_saas_edition


@dataclass
class HelpMenuButton:
    def __init__(self, name: str, url_pattern: str) -> None:
        self.name = name
        self.url_pattern = url_pattern


@pytest.fixture(
    name="help_menu_button",
    params=[
        pytest.param(
            HelpMenuButton("help_beginners_guide", "docs.checkmk.com"),
            id="beginners_guide",
        ),
        pytest.param(
            HelpMenuButton("help_user_manual", "docs.checkmk.com"),
            id="user_manual",
        ),
        pytest.param(
            HelpMenuButton("help_video_tutorials", "consent.youtube.com"),
            id="video_tutorials",
        ),
        pytest.param(
            HelpMenuButton("help_community_forum", "forum.checkmk.com"),
            id="community_forum",
        ),
        pytest.param(
            HelpMenuButton("help_plugin_api_intro", "docs.checkmk.com"),
            id="plugin_api_intro",
        ),
        pytest.param(
            HelpMenuButton("help_plugin_api_docs", "/check_mk/plugin-api/"),
            id="plugin_api_docs",
        ),
        pytest.param(
            HelpMenuButton("help_rest_api_intro", "docs.checkmk.com"),
            id="rest_api_intro",
        ),
        pytest.param(
            HelpMenuButton("help_rest_api_docs", "/check_mk/api/doc/"),
            id="rest_api_docs",
        ),
        pytest.param(
            HelpMenuButton("help_rest_api_gui", "/check_mk/api/.*/ui/"),
            id="rest_api_gui",
        ),
        pytest.param(
            HelpMenuButton("help_saas_status_page", "status.checkmk.com"),
            id="saas_status_page",
            marks=skip_if_not_saas_edition,
        ),
        pytest.param(
            HelpMenuButton("help_suggest_product_improvement", "ideas.checkmk.com"),
            id="suggest_product_improvement",
        ),
    ],
)
def fixture_help_menu_button(
    request: pytest.FixtureRequest, page: Page
) -> Iterator[HelpMenuButton]:
    def update_user_agent(route: Route, request: Request) -> None:
        headers = request.headers
        headers["user-agent"] = (
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0"
        )
        route.continue_(headers=headers)

    help_menu_button: HelpMenuButton = request.param
    browser_context = page.context
    if "ideas" in help_menu_button.url_pattern:
        # "ideas.checkmk.com" requires a reliable user_agent to be initialized,
        # not an automated one.
        browser_context.route(re.compile(help_menu_button.url_pattern), update_user_agent)
    yield help_menu_button
    browser_context.unroute_all()


def test_help_menu(
    dashboard_page: Dashboard,
    help_menu_button: HelpMenuButton,
) -> None:
    browser_context = dashboard_page.page.context
    pw_timeout_msg = (
        f"Expected a response to URL with pattern: `{help_menu_button.url_pattern}`.\n"
        "None intercepted within the validation period!"
    )

    with browser_context.expect_page() as new_tab_info:
        with browser_context.expect_event(
            "response",
            lambda response: bool(re.findall(help_menu_button.url_pattern, response.url)),
        ) as matched_response:
            getattr(dashboard_page.main_menu, help_menu_button.name).click()
            with handle_playwright_timeouterror(pw_timeout_msg):
                assert matched_response.value.status in (200, 301), (
                    f"Unexpected response status code: {matched_response.value.status}, "
                    f"response url: {matched_response.value.url}"
                )
            new_page = new_tab_info.value
            new_page.wait_for_url(url=re.compile(help_menu_button.url_pattern), wait_until="load")
            new_page.close()


def test_help_info(dashboard_page: Dashboard) -> None:
    dashboard_page.main_menu.help_info.click()
    dashboard_page.page.wait_for_url(url=re.compile("info.py$"), wait_until="load")
    dashboard_page.main_area.check_page_title("About Checkmk")
