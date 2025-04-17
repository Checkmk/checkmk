#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Definitions of timeouts during e2e testing."""

from collections.abc import Iterator
from contextlib import contextmanager

from playwright.sync_api import TimeoutError as PWTimeoutError

# timeout for playwright assertions (millseconds)
TIMEOUT_ACTIVATE_CHANGES_MS = 120_000
# timeout for playwright interactions (millseconds)
TIMEOUT_ASSERTIONS = TIMEOUT_NAVIGATION = TIMEOUT_ACTIVATE_CHANGES_MS
ANIMATION_TIMEOUT = 1000  # 750 ms (animation) + 250 ms (buffer)


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
