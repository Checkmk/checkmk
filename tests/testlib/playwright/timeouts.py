#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

""" definitions of timeouts during e2e testing
"""
from types import TracebackType
from typing import Type

from playwright.sync_api import Page

TIMEOUT_ACTIVATE_CHANGES_MS = 15000


class TemporaryTimeout:
    """Temporary change default timeout
    Use this context manager if you want to use custom timeouts.
    """

    default_timeout_ms = 30000

    def __init__(self, page: Page, temporary_timeout_ms: int) -> None:
        self.page = page
        self.timeout = temporary_timeout_ms

    def __enter__(self) -> None:
        self.page.set_default_timeout(self.timeout)

    def __exit__(
        self, exc_type: Type[BaseException], exc_value: BaseException, exc_tb: TracebackType
    ) -> None:
        self.page.set_default_timeout(self.default_timeout_ms)
