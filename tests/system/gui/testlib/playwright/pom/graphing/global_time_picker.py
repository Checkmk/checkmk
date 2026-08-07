#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Page object for the page's single global time picker.

One picker drives every graph on the page, so this is addressed off the main area rather than
off any one graph. It is rendered outside ``div#main_page_content`` (so it stays put while the
graph list scrolls), which ``MainArea.locator`` handles: with no ``iframe[name='main']`` it
falls back to the whole page.
"""

import logging

from playwright.sync_api import Locator

from tests.system.gui.testlib.playwright.pom.page import MainArea

logger = logging.getLogger(__name__)

_PICKER_SELECTOR = "div.graphing-global-time-picker"


class GlobalTimePicker:
    """The global time picker: its preset chips, its trigger and its refresh pill."""

    def __init__(self, main_area: MainArea) -> None:
        self._main_area = main_area

    @property
    def root(self) -> Locator:
        return self._main_area.locator(_PICKER_SELECTOR)

    @property
    def trigger(self) -> Locator:
        """The button opening the custom-range flyout."""
        return self.root.locator("button.graphing-global-time-picker__trigger")

    def preset_chip(self, name: str) -> Locator:
        """A preset chip by its configured title.

        By role, not by class: the picker keeps an off-screen replica of every chip to measure
        the overflow fit, so a CSS locator matches each preset twice. The replica is
        ``aria-hidden``, which the role engine skips.
        """
        return self.root.get_by_role("button", name=name, exact=True)

    @property
    def active_preset_chip(self) -> Locator:
        """The highlighted preset; empty once the window is a custom one.

        Safe as a CSS locator despite the measurement replica: those chips are never selected.
        """
        return self.root.locator('[aria-pressed="true"]')

    @property
    def overflow(self) -> Locator:
        """The "More time ranges" control, present only when the chips do not all fit."""
        return self.root.locator("div.graphing-dynamic-presets__overflow")

    def select_preset(self, name: str) -> None:
        """Click a preset chip, falling back to the overflow list when it does not fit.

        Which chips are visible depends on the viewport, so a test naming a preset should not
        have to care whether this one happened to be pushed into the overflow.
        """
        # ``count()`` does not auto-wait, and the picker mounts independently of the graphs:
        # without this, one slower than the first canvas reads as "no such chip".
        self.root.wait_for(state="visible")
        chip = self.preset_chip(name)
        if chip.count():
            logger.info("Selecting the time range preset '%s'", name)
            chip.click()
            return
        logger.info("Selecting the time range preset '%s' from the overflow", name)
        self.overflow.get_by_role("combobox").click()
        self.overflow.get_by_role("option", name=name, exact=True).click()

    @property
    def refresh_indicator(self) -> Locator:
        """The live/paused refresh pill beside the picker."""
        return self.root.locator(".graphing-global-refresh-control")

    @property
    def resume_refresh_button(self) -> Locator:
        return self.refresh_indicator.get_by_role("button", name="Resume")
