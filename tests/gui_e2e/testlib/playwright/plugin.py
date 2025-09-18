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
import typing as t
from collections.abc import Callable, Iterator

import pytest
from playwright._impl._api_structures import StorageState
from playwright.sync_api import BrowserContext, expect, Page
from pytest_playwright import CreateContextCallback

from tests.gui_e2e.testlib.playwright.timeouts import TIMEOUT_ACTIVATE_CHANGES

logger = logging.getLogger(__name__)

CLI_ARGUMENT_LOCALE = "--locale"
CLI_ARGUMENT_LOCAL_RUN = "--local-run"
CLI_ARGUMENT_GUI_TIMEOUT = "--gui-timeout"
CLI_ARGUMENT_TRACING = "--tracing"


PageGetter: t.TypeAlias = Callable[[BrowserContext], Page]


def positive_integer(value: str) -> int:
    integer_value = int(value)
    if integer_value <= 0:
        raise ValueError
    return integer_value


@pytest.fixture(scope="session")
def browser_context_args(
    browser_context_args: dict[str, t.Any], pytestconfig: pytest.Config
) -> dict[str, t.Any]:
    """Define and return arguments to initialize a playwright `BrowserContext` object.

    This overrides the default `browser_context_args` fixture provided by pytest-playwright.
    """
    _viewport = (
        {"width": 1600, "height": 900}
        if pytestconfig.getoption(CLI_ARGUMENT_LOCAL_RUN)
        else {"width": 1920, "height": 1080}
    )

    return {
        **browser_context_args,
        "locale": pytestconfig.getoption(CLI_ARGUMENT_LOCALE),
        "viewport": _viewport,
    }


@pytest.fixture(name="browser_storage_state", scope="module")
def fixture_browser_storage_stage() -> StorageState:
    """Create a storage state for the browser context.

    This fixture is used to initialize the browser context with cookies and local storage data.
    It returns an empty `StorageState` object, which can be updated later with actual data.
    """
    return StorageState()


@pytest.fixture(scope="session", autouse=True)
def get_new_page(pytestconfig: pytest.Config) -> PageGetter:
    """Return a callable that creates a new page with the specified timeout."""
    timeout_value = pytestconfig.getoption(CLI_ARGUMENT_GUI_TIMEOUT) * 1000

    expect.set_options(timeout=timeout_value)

    def _get_new_page(_context: BrowserContext) -> Page:
        page = _context.new_page()
        page.set_default_timeout(timeout_value)
        page.set_default_navigation_timeout(timeout_value)
        return page

    return _get_new_page


@pytest.fixture
def cmk_page(
    new_context: CreateContextCallback,
    browser_storage_state: StorageState,
    get_new_page: PageGetter,
) -> Iterator[Page]:
    """Create a new browser context and page for each test.

    It uses the `browser_storage_state` fixture to initialize the context with
    the previous storage state, which contains cookies and local storage data.
    This allows the page to start with a pre-defined state, such as being logged in.
    """
    context = new_context(storage_state=browser_storage_state)

    yield get_new_page(context)

    browser_storage_state.update(context.storage_state())


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


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom CLI arguments to GUI end to end testing framework."""
    group = parser.getgroup("playwright", "Playwright")
    group.addoption(
        CLI_ARGUMENT_LOCALE,
        default="en-US",
        help="The default locale of the browser.",
    )
    group.addoption(
        CLI_ARGUMENT_LOCAL_RUN,
        action="store_true",
        help="Adapt certain settings for running testsuite locally.\n+ viewport size: 1600 x 900",
    )
    group.addoption(
        CLI_ARGUMENT_GUI_TIMEOUT,
        type=positive_integer,
        default=TIMEOUT_ACTIVATE_CHANGES,
        help=(
            "Set the timeout for Playwright actions (in seconds)."
            f" Default is {TIMEOUT_ACTIVATE_CHANGES}."
        ),
    )


def pytest_sessionstart(session: pytest.Session) -> None:
    """Perform operations at the very starting of a testsuite run."""

    def cli_arg_to_attribute(cli_arg: str) -> str:
        return session.config._opt2dest.get(cli_arg, cli_arg)

    def is_cli_arg_used(cli_arg: str) -> bool:
        return any(cli_arg in _.split("=") for _ in session.config.invocation_params.args)

    # Override default values of '--gui-timeout' and '--tracing' on '--local-run' usage.
    if session.config.getoption(CLI_ARGUMENT_LOCAL_RUN):
        if not is_cli_arg_used(CLI_ARGUMENT_GUI_TIMEOUT):
            setattr(
                session.config.option,
                cli_arg_to_attribute(CLI_ARGUMENT_GUI_TIMEOUT),
                15,  # seconds
            )

        if not is_cli_arg_used(CLI_ARGUMENT_TRACING):
            setattr(
                session.config.option,
                cli_arg_to_attribute(CLI_ARGUMENT_TRACING),
                "retain-on-failure",
            )
