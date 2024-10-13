#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from pathlib import Path

from playwright.sync_api import expect, Locator, Page

logger = logging.getLogger(__name__)


class EmailPage:
    def __init__(
        self,
        page: Page,
        file_path: Path,
    ) -> None:
        self.page = page
        self.file_link = f"file://{file_path}"
        self.navigate()

    def navigate(self) -> None:
        logger.info("Open email html file in browser")
        self.page.goto(self.file_link, wait_until="load")

    def row_value(self, row_name: str) -> Locator:
        return self.page.locator(f"tr:has-text('{row_name}') >> td").nth(1)

    def check_table_content(self, expected_content: dict) -> None:
        for row_name, expected_value in expected_content.items():
            expect(self.row_value(row_name)).to_have_text(expected_value)
