#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""some fixtures

the pytest-playwright addon's fixtures are too "aggressive" and are loaded in
all tests. So some functionality is inspired from this module
See: https://github.com/microsoft/playwright-pytest
"""

import logging
import os
import typing as t

import pytest
from _pytest.fixtures import (
    SubRequest,  # TODO: Do we really need an implementation detail?
)
from playwright.sync_api import (
    Browser,
    BrowserContext,
    BrowserType,
    Error,
    Page,
    Playwright,
    sync_playwright,
)

logger = logging.getLogger(__name__)
_browser_engines = ["chromium", "firefox"]  # engines selectable via CLI
_browser_engines_ci = ["chromium"]  # align with what playwright installs in the CI (see Makefile)
_mobile_devices = ["iPhone 6", "Galaxy S8"]


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


def _build_artifact_path(
    pytestconfig: t.Any, request: pytest.FixtureRequest, suffix: str = ""
) -> str:
    output_dir = pytestconfig.getoption("--output")
    node_safepath = os.path.splitext(os.path.split(request.node.path)[1])[0]
    node_safename = request.node.name.replace("[", "__").replace("]", "__")
    build_artifact_path = os.path.join(output_dir, f"{node_safepath}__{node_safename}{suffix}")
    logger.debug("build_artifact_path=%s", build_artifact_path)

    return build_artifact_path


@pytest.fixture(scope="session", name="playwright")
def _playwright() -> t.Generator[Playwright, None, None]:
    pw = sync_playwright().start()
    yield pw
    pw.stop()


@pytest.fixture(scope="session", name="browser_type")
def _browser_type(playwright: Playwright, browser_name: str) -> BrowserType:
    return t.cast(BrowserType, getattr(playwright, browser_name))


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
    pages: t.List[Page] = []
    context = browser.new_context(
        locale=pytestconfig.getoption("--locale"), viewport={"width": 1920, "height": 1080}
    )
    context.on("page", lambda page: pages.append(page))  # pylint: disable=unnecessary-lambda
    yield context
    try:
        _may_create_screenshot(request, pytestconfig, pages)
    finally:
        context.close()


@pytest.fixture(name="context_mobile", params=_mobile_devices)
def _context_mobile(
    playwright: Playwright,
    browser: Browser,
    pytestconfig: t.Any,
    request: pytest.FixtureRequest,
    is_chromium: bool,  # pylint: disable=redefined-outer-name
) -> t.Generator[BrowserContext, None, None]:
    if not is_chromium:
        pytest.skip("Mobile emulation currently not supported on Firefox.")

    devices = playwright.devices[str(request.param)]
    pages: t.List[Page] = []

    context = browser.new_context(locale=pytestconfig.getoption("--locale"), **devices)
    context.on("page", lambda page: pages.append(page))  # pylint: disable=unnecessary-lambda
    yield context
    try:
        _may_create_screenshot(request, pytestconfig, pages)
    finally:
        context.close()


def _may_create_screenshot(
    request: pytest.FixtureRequest,
    pytestconfig: t.Any,
    pages: t.List[Page],
) -> None:
    failed = request.node.rep_call.failed if hasattr(request.node, "rep_call") else True
    screenshot_option = pytestconfig.getoption("--screenshot")
    capture_screenshot = screenshot_option == "on" or (
        failed and screenshot_option == "only-on-failure"
    )
    if not capture_screenshot:
        return
    for page in pages:
        human_readable_status = "failed" if failed else "finished"
        screenshot_path = _build_artifact_path(
            pytestconfig, request, f".{human_readable_status}.png"
        )
        try:
            page.screenshot(timeout=5432, path=screenshot_path)
        except Error as e:
            logger.info("Failed to create screenshot of page %s due to: %s", page, e)


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


@pytest.fixture(name="browser_name", scope="session", params=_browser_engines)
def _browser_name(request: SubRequest, pytestconfig: pytest.Config) -> str:
    """Returns the browser name(s).

    Fixture returning the parametrized browser name(s). A subset of the parametrized browser names
    can be selected via the --browser flag in the CLI.
    """
    browser_name_param = str(request.param)
    browser_names_cli = t.cast(list[str], pytestconfig.getoption("--browser"))

    if browser_name_param not in browser_names_cli and not len(browser_names_cli) == 0:
        pytest.skip(
            f"Only {', '.join(str(browser) for browser in browser_names_cli)} engine(s) selected "
            f"from the CLI"
        )
    elif len(browser_names_cli) == 0 and browser_name_param not in _browser_engines_ci:
        pytest.skip(f"{browser_name_param} engine not running in the CI. Still selectable via CLI")
    return browser_name_param


# Making test result information available in fixtures
# https://docs.pytest.org/en/latest/example/simple.html#making-test-result-information-available-in-fixtures
# NOTE: hookimpl is poorly typed, so the decorator effectively removes the types from the decorated function!
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: t.Any) -> t.Generator[None, t.Any, None]:
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()

    # set a report attribute for each phase of a call, which can
    # be "setup", "call", "teardown"

    setattr(item, "rep_" + rep.when, rep)


def pytest_addoption(parser: t.Any) -> None:
    group = parser.getgroup("playwright", "Playwright")
    group.addoption(
        "--browser",
        action="append",
        default=[],
        help="Browser engine which should be used",
        choices=_browser_engines,
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
    group.addoption(
        "--output",
        default="test-results",
        help="Directory for artifacts produced by tests, defaults to test-results.",
    )
    group.addoption(
        "--screenshot",
        default="only-on-failure",
        choices=["on", "off", "only-on-failure"],
        help="Whether to automatically capture a screenshot after each test. "
        "If you choose only-on-failure, a screenshot of the failing page only will be created.",
    )
    group.addoption("--locale", default="en-US", help="The default locale of the browser.")
