#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Definitions of timeouts during e2e testing."""

from contextlib import contextmanager
from types import TracebackType
from typing import Iterator

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PWTimeoutError

# timeout for playwright assertions (millseconds
TIMEOUT_ACTIVATE_CHANGES_MS = 15_000
# timeout for playwright interactions (millseconds)
TIMEOUT_ASSERTIONS = TIMEOUT_NAVIGATION = 2 * TIMEOUT_ACTIVATE_CHANGES_MS


class TemporaryTimeout:
    """Temporary change default timeout
    Use this context manager if you want to use custom timeouts.
    """

    default_timeout_ms = TIMEOUT_NAVIGATION

    def __init__(self, page: Page, temporary_timeout_ms: int) -> None:
        self.page = page
        self.timeout = temporary_timeout_ms

    def __enter__(self) -> None:
        self.page.set_default_timeout(self.timeout)

    def __exit__(
        self, exc_type: type[BaseException], exc_value: BaseException, exc_tb: TracebackType
    ) -> None:
        self.page.set_default_timeout(self.default_timeout_ms)


@contextmanager
def handle_playwright_timeouterror(msg: str) -> Iterator:
    """Handle and update `playwright.sync_api::TimeoutError` with a context specific message.

    Enables easy debugging when a test fails due to timeout issues.
    """
    try:
        yield
    except PWTimeoutError as excp:
        excp.add_note(msg)
        raise excp
