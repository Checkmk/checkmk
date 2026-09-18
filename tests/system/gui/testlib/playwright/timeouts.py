#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Definitions of timeouts during e2e testing."""

# mypy: disable-error-code="type-arg"

from collections.abc import Iterator
from contextlib import contextmanager

from playwright.sync_api import TimeoutError as PWTimeoutError

# timeout for playwright assertions
TIMEOUT_EXPECT_CHANGES = 120
TIMEOUT_EXPECT_CHANGES_MS = TIMEOUT_EXPECT_CHANGES * 1000
# timeout for ui animations
ANIMATION_TIMEOUT = 1000  # 750 ms (animation) + 250 ms (buffer)
# timeout for AI response (mocked routes, so network is instant; allow for rendering overhead)
TIMEOUT_AI_RESPONSE = 10_000
# timeout for a dashboard whose initial render blocks on a slow server-side computation
# (e.g. the average-scatterplot widget's mean/median over RRD data)
TIMEOUT_SLOW_DASHBOARD_LOAD_MS = 240_000


@contextmanager
def handle_playwright_timeouterror(msg: str) -> Iterator:  # type: ignore[misc]
    """Handle and update `playwright.sync_api::TimeoutError` with a context specific message.

    Enables easy debugging when a test fails due to timeout issues.
    """
    try:
        yield
    except PWTimeoutError as excp:
        excp.add_note(msg)
        raise excp
