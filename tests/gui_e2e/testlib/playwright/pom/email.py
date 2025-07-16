#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

from playwright.sync_api import Locator, Page

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

    def _get_row(self, row_name: str) -> Locator:
        return self.page.locator(f"tr:has(> td:text-is('{row_name}'))")

    def get_field_value(self, field_name: str) -> str:
        """Get the value of the specified field from the rendered HTML email."""
        value = self._get_row(field_name).inner_text()
        value = value.replace("\n", "").replace("\t", "")
        return value.split(field_name, 1)[1]

    def check_table_content(self, expected_content: dict) -> None:
        """Check that the rendered HTML email contains the expected content."""
        for field, expected_value in expected_content.items():
            field_name = field + ":"
            field_value = self.get_field_value(field_name)
            assert field_value == expected_value, (
                f"Unexpected valued of field '{field_name}'. "
                f"Expected value: {expected_value}, actual value: {field_value}"
            )
