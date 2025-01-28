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
import re
import typing as t
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from playwright.sync_api import (
    Browser,
    BrowserContext,
    BrowserType,
    Error,
    Page,
    Playwright,
    sync_playwright,
    Video,
)

from tests.testlib.pytest_helpers.calls import exit_pytest_on_exceptions

logger = logging.getLogger(__name__)
_browser_engines = ["chromium", "firefox"]  # engines selectable via CLI
_browser_engines_ci = ["chromium"]  # align with what playwright installs in the CI (see Makefile)
_mobile_devices = ["iPhone 6", "Galaxy S8"]


@pytest.fixture(scope="session", name="browser_type_launch_args")
def fixture_browser_type_launch_args(pytestconfig: t.Any) -> dict:
    """Return arguments to initialize playwright `Browser`_ object.

    .. _Browser: https://playwright.dev/python/docs/api/class-browser
    """
    launch_options = {}
    headed_option = pytestconfig.getoption("--headed")
    if headed_option:
        launch_options["headless"] = False
    slowmo_option = pytestconfig.getoption("--slowmo")
    if slowmo_option:
        launch_options["slow_mo"] = slowmo_option
    return launch_options


def _build_artifact_path(
    request: pytest.FixtureRequest, artifact_name: str = "", suffix: str = ""
) -> Path:
    output_dir = request.config.getoption("--output")
    node_safepath = os.path.splitext(os.path.split(request.node.path)[1])[0]
    # replace `[]`, `()`, whitespaces with `_`.
    _name = re.sub(
        r"[\[\]\(\)\s]",
        "_",
        f"{artifact_name}" if artifact_name else f"{node_safepath}__{request.node.name}",
    )
    build_artifact_path = Path(output_dir).absolute() / f"{_name}{suffix}"
    logger.debug("build_artifact_path=%s", build_artifact_path)
    return build_artifact_path


@pytest.fixture(scope="session")
def _playwright() -> t.Generator[Playwright, None, None]:
    pw = sync_playwright().start()
    yield pw
    pw.stop()


@pytest.fixture(scope="session")
def _browser_type(_playwright: Playwright, browser_name: str) -> BrowserType:
    return t.cast(BrowserType, getattr(_playwright, browser_name))


@pytest.fixture(scope="session")
def _browser(
    _browser_type: BrowserType, browser_type_launch_args: dict
) -> t.Generator[Browser, None, None]:
    with exit_pytest_on_exceptions(
        exceptions=(Error,), exit_msg="Install playwright within the environment!"
    ):
        browser = _browser_type.launch(**browser_type_launch_args)
    yield browser
    browser.close()


@pytest.fixture(name="context_launch_kwargs", scope="session")
def fixture_context_launch_kwargs(pytestconfig: pytest.Config) -> dict[str, t.Any]:
    """Define and return arguments to initialize a playwright `BrowserContext`_ object.

    .. _BrowserContext: https://playwright.dev/python/docs/api/class-browsercontext
    """
    kwargs = {"locale": pytestconfig.getoption("--locale")}
    if pytestconfig.getoption("--video"):
        kwargs["record_video_dir"] = str(pytestconfig.getoption("--output"))
        kwargs["record_video_size"] = {"width": 1280, "height": 960}
    return kwargs


@pytest.fixture(scope="module")
def _context(
    _browser: Browser,
    context_launch_kwargs: dict[str, t.Any],
) -> t.Generator[BrowserContext, None, None]:
    """Create a browser context(browser testing) for one test-module at a time."""
    with manage_new_browser_context(_browser, context_launch_kwargs) as context:
        yield context


@pytest.fixture(scope="module", params=_mobile_devices)
def _context_mobile(
    _playwright: Playwright,
    _browser: Browser,
    context_launch_kwargs: dict[str, t.Any],
    request: pytest.FixtureRequest,
) -> t.Generator[BrowserContext, None, None]:
    """Create a browser context(mobile testing) for one test-module at a time."""
    devices = _playwright.devices[str(request.param)]
    with manage_new_browser_context(_browser, (context_launch_kwargs | devices)) as context:
        yield context


@contextmanager
def manage_new_browser_context(
    browser: Browser, context_kwargs: dict[str, t.Any] | None = None
) -> Iterator[BrowserContext]:
    """Creates a browser context and makes sure to close it (contextmanager).

    `context_kwargs` are the arguments passed to `BrowserContext`_.

    .. _BrowserContext: https://playwright.dev/python/docs/api/class-browsercontext
    """
    if not context_kwargs:
        context_kwargs = {}
    context = browser.new_context(**context_kwargs)
    try:
        yield context
    finally:
        context.close()


@pytest.fixture(name="page")
def fixture_page(
    _context: BrowserContext, request: pytest.FixtureRequest
) -> t.Generator[Page, None, None]:
    """Create a new page in a browser for every test-case."""
    with manage_new_page_from_browser_context(_context, request) as page:
        yield page


@pytest.fixture(name="page_mobile")
def fixture_page_mobile(
    _context_mobile: BrowserContext,
    is_chromium: bool,
    request: pytest.FixtureRequest,
) -> t.Generator[Page, None, None]:
    """Create a new page in a mobile browser for every test-case."""
    if not is_chromium:
        pytest.skip("Mobile emulation currently not supported on Firefox.")
    with manage_new_page_from_browser_context(_context_mobile, request) as page:
        yield page


@contextmanager
def manage_new_page_from_browser_context(
    context: BrowserContext,
    request: pytest.FixtureRequest | None = None,
    video_name: str = "",
) -> Iterator[Page]:
    """Create a new page from the provided `BrowserContext` and close it (contextmanager).

    Optionally, includes functionality
        * to take a screenshot when a test-case fails.
        * to record interactions occuring on the page.
            + videos are recorded within the directory provided to `--output`
            + custom `video_name` can be provided, exclude file extension.

        NOTE: requires access to pytest fixture: `request`.
    """
    pages: t.List[Page] = []
    context.on("page", lambda page: pages.append(page))
    page = context.new_page()
    try:
        yield page
    finally:
        _may_create_screenshot(request, pages)
        page.close()
        _may_record_video(page, request, video_name)


def _may_create_screenshot(
    request: pytest.FixtureRequest | None,
    pages: t.List[Page],
) -> None:
    if isinstance(request, pytest.FixtureRequest):
        failed = request.node.rep_call.failed if hasattr(request.node, "rep_call") else False
        screenshot_option = request.config.getoption("--screenshot")
        capture_screenshot = screenshot_option == "on" or (
            failed and screenshot_option == "only-on-failure"
        )
        if not capture_screenshot:
            return
        for page in pages:
            human_readable_status = "failed" if failed else "finished"
            screenshot_path = _build_artifact_path(request, suffix=f"{human_readable_status}.png")
            try:
                page.screenshot(timeout=5432, path=screenshot_path)
            except Error as e:
                logger.info("Failed to create screenshot of page %s due to: %s", page, e)


def _may_record_video(page: Page, request: pytest.FixtureRequest | None, video_name: str) -> None:
    if isinstance(request, pytest.FixtureRequest) and isinstance(page.video, Video):
        new_path = _build_artifact_path(request, artifact_name=video_name, suffix=".webm")
        logger.info("Video recorded at: %s", Path(page.video.path()).replace(new_path))
    else:
        logger.debug("Video recording is disabled.")


@pytest.fixture(scope="session", name="is_webkit")
def fixture_is_webkit(browser_name: str) -> bool:
    """Identify whether browser is Webkit."""
    return browser_name == "webkit"


@pytest.fixture(scope="session", name="is_firefox")
def fixture_is_firefox(browser_name: str) -> bool:
    """Identify whether browser is Firefox."""
    return browser_name == "firefox"


@pytest.fixture(scope="session", name="is_chromium")
def fixture_is_chromium(browser_name: str) -> bool:
    """Identify whether browser is Chromium."""
    return browser_name == "chromium"


@pytest.fixture(scope="session", name="browser_name", params=_browser_engines)
def fixture_browser_name(request: pytest.FixtureRequest) -> str:
    """Returns the browser name(s).

    Fixture returning the parametrized browser name(s). A subset of the parametrized browser names
    can be selected via the --browser flag in the CLI.
    """
    browser_name_param = str(request.param)
    browser_names_cli = t.cast(list[str], request.config.getoption("--browser"))

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
    """Set a report attribute for each phase of a pytest test execution call.

    Phases can be "setup", "call", "teardown.
    """
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)


def pytest_addoption(parser: t.Any) -> None:
    """Add custom CLI arguments to GUI end to end testing framework."""
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
    group.addoption(
        "--video",
        action="store_true",
        default=False,
        help="Record a video of interactions occurring in a page.",
    )
