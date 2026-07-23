#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging

from playwright.sync_api import Locator

logger = logging.getLogger(__name__)


class SearchOperatorSelect:
    """Represents the unified search search operator select"""

    def __init__(self, locator: Locator) -> None:
        self.locator = locator

    @property
    def button(self) -> Locator:
        return self.locator.get_by_role("button")

    def select(self, operator_name: str) -> None:
        self.button.click()
        self.locator.get_by_role("option", name=operator_name).click()

    def value(self) -> str:
        return self.button.inner_text()
