#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The time range setting a widget wizard offers on its visualization stage.

A widget either follows the dashboard's time range or uses a separate one, picked from the
widget's own range selector: a row of preset chips, with the presets that do not fit moved
into a "More time ranges" dropdown.
"""

import logging

from playwright.sync_api import expect, Locator

from tests.testlib.common.utils import wait_until

logger = logging.getLogger(__name__)

_LAYOUT_TIMEOUT_SECONDS = 10
# A few frames: long enough for the row to have measured and trimmed in between two reads.
_LAYOUT_SAMPLE_SECONDS = 0.25

FOLLOW_DASHBOARD_LABEL = "Follow dashboard time range"
SEPARATE_RANGE_LABEL = "Use separate time range"


class WidgetTimeRangeSettings:
    """The 'Time range' field of a widget wizard.

    Args:
        wizard: the wizard's sidebar, scoping every locator below.
    """

    def __init__(self, wizard: Locator) -> None:
        self._wizard = wizard

    @property
    def follow_dashboard_radio(self) -> Locator:
        return self._wizard.get_by_role("radio", name=FOLLOW_DASHBOARD_LABEL, exact=True)

    @property
    def separate_range_radio(self) -> Locator:
        return self._wizard.get_by_role("radio", name=SEPARATE_RANGE_LABEL, exact=True)

    @property
    def range_selector(self) -> Locator:
        """The widget's own range selector, shown only while it uses a separate range."""
        return self._wizard.locator(".lib-time-range-preset-row")

    @property
    def _chips(self) -> Locator:
        """The preset chips that fit the row.

        By role, not by class: the row keeps an off-screen, ``aria-hidden`` replica of every
        chip to measure the fit, which the role engine skips. The overflow dropdown's trigger
        is a combobox, so no other button is matched.
        """
        return self.range_selector.get_by_role("button")

    @property
    def _overflow(self) -> Locator:
        """The "More time ranges" dropdown, present only when the chips do not all fit."""
        return self.range_selector.locator(".lib-time-range-preset-row__overflow")

    def _open_overflow(self) -> Locator:
        """Open the overflow dropdown and return the options it offers."""
        self._overflow.get_by_role("combobox").click()
        options = self._overflow.get_by_role("option")
        expect(options.first, "The 'More time ranges' dropdown did not open").to_be_visible()
        return options

    def _close_overflow(self) -> None:
        self._overflow.get_by_role("combobox").press("Escape")

    def _wait_until_laid_out(self) -> None:
        """Wait for the row to settle on which chips fit.

        The row measures the fit after it renders, and only then trims chips into the
        overflow dropdown, so a read right after it appears can see every chip and no
        overflow. Settled once two reads a few frames apart agree.
        """
        expect(self._chips.first, "The range selector shows no preset at all").to_be_visible()
        previous: tuple[int, int] | None = None

        def unchanged() -> bool:
            nonlocal previous
            current = (self._chips.count(), self._overflow.count())
            settled = current == previous
            previous = current
            return settled

        wait_until(
            unchanged,
            timeout=_LAYOUT_TIMEOUT_SECONDS,
            interval=_LAYOUT_SAMPLE_SECONDS,
            condition_name="the range selector to settle on the chips that fit",
        )

    def offered_ranges(self) -> list[str]:
        """Every range the selector offers, in order: the chips, then the overflow's options."""
        self._wait_until_laid_out()
        ranges = [chip.inner_text().strip() for chip in self._chips.all()]
        if self._overflow.count():
            options = self._open_overflow()
            ranges += [option.get_attribute("aria-label") or "" for option in options.all()]
            self._close_overflow()
        return ranges

    def select_range(self, name: str) -> None:
        """Pick a range, from the overflow dropdown if its chip does not fit the row."""
        self._wait_until_laid_out()
        chip = self.range_selector.get_by_role("button", name=name, exact=True)
        if chip.count():
            logger.info("Selecting the widget time range '%s'", name)
            chip.click()
            return
        logger.info("Selecting the widget time range '%s' from the overflow", name)
        self._open_overflow()
        self._overflow.get_by_role("option", name=name, exact=True).click()

    def selected_range(self) -> str | None:
        """The range the selector marks as picked, or None if it marks none."""
        self._wait_until_laid_out()
        pressed = self.range_selector.get_by_role("button", pressed=True)
        if pressed.count():
            return pressed.inner_text().strip()
        if not self._overflow.count():
            return None
        self._open_overflow()
        selected = self._overflow.get_by_role("option", selected=True)
        name = selected.get_attribute("aria-label") if selected.count() else None
        self._close_overflow()
        return name
