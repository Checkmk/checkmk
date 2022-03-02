#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""some fixtures

the pytest-playwright addon's fixtures are too "aggressive" and are loaded in
all tests. So some functionality is inspierd from this module
See: https://github.com/microsoft/playwright-pytest
"""

import typing as t

import pytest
from playwright.sync_api import (
    Browser,
    BrowserContext,
    BrowserType,
    Page,
    Playwright,
    sync_playwright,
)


@pytest.fixture(scope="session", name="browser_type_launch_args")
def _browser_type_launch_args(pytestconfig: t.Any) -> dict:
    launch_options = {}
    headed_option = pytestconfig.getoption("--headed")
    if headed_option:
        launch_options["headless"] = False
    slowmo_option = pytestconfig.getoption("--slowmo")
    if slowmo_option:
        launch_options["slow_mo"] = slowmo_option
    return launch_options


@pytest.fixture(scope="session", name="playwright")
def _playwright() -> t.Generator[Playwright, None, None]:
    pw = sync_playwright().start()
    yield pw
    pw.stop()


@pytest.fixture(scope="session", name="browser_type")
def _browser_type(playwright: Playwright, browser_name: str) -> BrowserType:
    return getattr(playwright, browser_name)


@pytest.fixture(scope="session", name="browser")
def _browser(
    browser_type: BrowserType, browser_type_launch_args: dict
) -> t.Generator[Browser, None, None]:
    browser = browser_type.launch(**browser_type_launch_args)
    yield browser
    browser.close()


@pytest.fixture(name="context")
def _context(
    browser: Browser,
    pytestconfig: t.Any,
    request: pytest.FixtureRequest,
) -> t.Generator[BrowserContext, None, None]:
    context = browser.new_context()
    yield context
    context.close()


@pytest.fixture(name="page")
def _page(context: BrowserContext) -> t.Generator[Page, None, None]:
    page = context.new_page()
    yield page


@pytest.fixture(scope="session")
def is_webkit(browser_name: str) -> bool:
    return browser_name == "webkit"


@pytest.fixture(scope="session")
def is_firefox(browser_name: str) -> bool:
    return browser_name == "firefox"


@pytest.fixture(scope="session")
def is_chromium(browser_name: str) -> bool:
    return browser_name == "chromium"


@pytest.fixture(name="browser_name", scope="session")
def _browser_name(pytestconfig: t.Any) -> t.Optional[str]:
    browser_names = pytestconfig.getoption("--browser")
    if len(browser_names) == 0:
        return "chromium"
    if len(browser_names) == 1:
        return browser_names[0]
    raise NotImplementedError("When using unittest specifying multiple browsers is not supported")


def pytest_addoption(parser: t.Any) -> None:
    group = parser.getgroup("playwright", "Playwright")
    group.addoption(
        "--browser",
        action="append",
        default=[],
        help="Browser engine which should be used",
        choices=["chromium", "firefox", "webkit"],
    )
    group.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="Run tests in headed mode.",
    )
    group.addoption(
        "--slowmo",
        default=0,
        type=int,
        help="Run tests with slow mo",
    )
