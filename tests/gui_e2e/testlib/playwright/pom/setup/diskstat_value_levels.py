#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

from playwright.sync_api import Locator

from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.gui_e2e.testlib.playwright.pom.setup.predictive_level_helpers import (
    LevelType,
    PredictiveLevelTypeShort,
)

logger = logging.getLogger(__name__)


class DiskstatValueLevels:
    """Class for Levels configuration of Value section in Ruleset of 'Disk IO levels' page."""

    def __init__(self, page: CmkPage, checkbox_label: str):
        """
        Args:
            base_locator: Base locator of Levels section to search within
            checkbox_label: Text of the top-level checkbox label (e.g., "Levels on CPU load: 1 minute average")
        """
        self.page = page
        self.checkbox_label = checkbox_label

    @property
    def _value_section(self) -> Locator:
        return self.page.main_area.locator(
            f"td.dictleft:has(label.cmk-checkbox span:has-text('{self.checkbox_label}'))"
        )

    # === Main Level Control ===
    @property
    def enable_levels_checkbox(self) -> Locator:
        """Main checkbox to enable/disable levels."""
        return self._value_section.locator(
            f"label.cmk-checkbox:has-text('{self.checkbox_label}') button[role='checkbox']"
        )

    @property
    def level_type_dropdown(self) -> Locator:
        """Dropdown to select level type (No Levels, Fixed, Predictive)."""
        return self._value_section.get_by_role("combobox", name=self.checkbox_label)

    def enable_levels(self) -> None:
        """Enable levels by checking the main checkbox."""
        logger.info("Enabling levels for: %s", self.checkbox_label)
        self.enable_levels_checkbox.click()
        self.level_type_dropdown.wait_for(state="visible")

    def set_level_type(self, level_type: LevelType) -> None:
        """Set the level type (No Levels, Fixed, or Predictive).

        Args:
            level_type: The type of levels to configure
        """
        self.level_type_dropdown.click()
        logger.info("Setting level type to: %s for %s", level_type.value, self.checkbox_label)
        self._value_section.get_by_role("listbox").get_by_role(
            "option", name=level_type.value
        ).click()

    def set_predictive_level_type(self, level_type: PredictiveLevelTypeShort) -> None:
        """Set the predictive level type (Absolute, Relative, Standard Deviation).

        Args:
            level_type: The type of predictive levels to configure
        """
        self._value_section.get_by_role("combobox", name="Level definition in relation").click()
        logger.info(
            "Setting predictive level type to: %s for %s", level_type.value, self.checkbox_label
        )
        self._value_section.get_by_role("listbox").get_by_role(
            "option", name=level_type.value
        ).click()
