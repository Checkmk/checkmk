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
from collections.abc import Iterator

import pytest
from playwright._impl._api_structures import StorageState
from playwright.sync_api import Page
from pytest_playwright import CreateContextCallback

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def browser_context_args(
    browser_context_args: dict[str, t.Any], pytestconfig: pytest.Config
) -> dict[str, t.Any]:
    """Define and return arguments to initialize a playwright `BrowserContext` object.

    This overrides the default `browser_context_args` fixture provided by pytest-playwright.
    """
    _viewport = (
        {"width": 1600, "height": 900}
        if pytestconfig.getoption("--local-run")
        else {"width": 1920, "height": 1080}
    )

    return {
        **browser_context_args,
        "locale": pytestconfig.getoption("--locale"),
        "viewport": _viewport,
    }


@pytest.fixture(name="browser_storage_state", scope="module")
def fixture_browser_storage_stage() -> StorageState:
    """Create a storage state for the browser context.

    This fixture is used to initialize the browser context with cookies and local storage data.
    It returns an empty `StorageState` object, which can be updated later with actual data.
    """
    return StorageState()


@pytest.fixture
@pytest.mark.browser_context_args
def cmk_page(
    new_context: CreateContextCallback, browser_storage_state: StorageState
) -> Iterator[Page]:
    """Create a new browser context and page for each test.

    It uses the `browser_storage_state` fixture to initialize the context with
    the previous storage state, which contains cookies and local storage data.
    This allows the page to start with a pre-defined state, such as being logged in.
    """
    context = new_context(storage_state=browser_storage_state)

    yield context.new_page()

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
        "--locale",
        default="en-US",
        help="The default locale of the browser.",
    )
    group.addoption(
        "--local-run",
        action="store_true",
        help="Adapt certain settings for running testsuite locally.\n+ viewport size: 1600 x 900",
    )
