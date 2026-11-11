#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The legend setting a graph widget wizard offers in its 'Additional graph options'.

A graph widget shows no legend, a compact one or an extended one: the 'Show graph legend'
checkbox switches the legend on, and only then offers the compact and the extended style as
radio buttons.
"""

import re
from enum import StrEnum

from playwright.sync_api import expect, Locator

from tests.testlib.common.utils import wait_until

SHOW_LEGEND_LABEL = "Show graph legend"
_PANEL_TOGGLE_LABEL = "Toggle Additional graph options"


class GraphLegendMode(StrEnum):
    """What a graph widget shows as its legend."""

    NO_LEGEND = "No legend"
    COMPACT = "Compact"
    EXTENDED = "Extended"


# The modes offered as a style once the legend is shown, by the label of their radio button.
LEGEND_STYLES = (GraphLegendMode.COMPACT, GraphLegendMode.EXTENDED)


class WidgetGraphLegendSettings:
    """The 'Legend' row of a graph widget wizard.

    The row is part of the 'Additional graph options' panel, which starts out collapsed; every
    action below opens it first.

    Args:
        wizard: the wizard's sidebar, scoping every locator below.
    """

    def __init__(self, wizard: Locator) -> None:
        self._wizard = wizard

    @property
    def _row(self) -> Locator:
        # The row's description is plain text, not a label tied to its fields.
        description = self._wizard.page.locator(
            ".db-field-description__label", has_text=re.compile(r"^\s*Legend\s*$")
        )
        return self._wizard.locator(".table-form-row").filter(has=description)

    @property
    def _panel_toggle(self) -> Locator:
        return self._wizard.get_by_role("button", name=_PANEL_TOGGLE_LABEL, exact=True)

    def reveal(self) -> None:
        """Open the 'Additional graph options' panel until the row shows.

        Retried rather than clicked once: the stage renders its panels only after it loaded
        the widget, and may render them again collapsed, so a single early click gets lost.
        """

        def _row_shown() -> bool:
            if self.show_legend_checkbox.is_visible():
                return True
            toggle = self._panel_toggle
            if toggle.is_visible() and toggle.get_attribute("aria-expanded") == "false":
                toggle.click()
            return False

        wait_until(
            _row_shown,
            timeout=30,
            interval=0.5,
            condition_name="the legend setting to show in 'Additional graph options'",
        )

    @property
    def show_legend_checkbox(self) -> Locator:
        return self._row.get_by_role("checkbox", name=SHOW_LEGEND_LABEL, exact=True)

    @property
    def style_radios(self) -> Locator:
        """Every legend style the row offers, present only while the legend is shown."""
        return self._row.get_by_role("radio")

    def style_radio(self, style: GraphLegendMode) -> Locator:
        return self._row.get_by_role("radio", name=style, exact=True)

    def select_mode(self, mode: GraphLegendMode) -> None:
        self.reveal()
        if mode is GraphLegendMode.NO_LEGEND:
            self.show_legend_checkbox.uncheck()
            return
        self.show_legend_checkbox.check()
        self.style_radio(mode).check()

    def expect_mode(self, mode: GraphLegendMode, message: str) -> None:
        """Wait for the row to show the mode as picked."""
        self.reveal()
        if mode is GraphLegendMode.NO_LEGEND:
            expect(self.show_legend_checkbox, message).not_to_be_checked()
            expect(self.style_radios, message).to_have_count(0)
            return
        expect(self.show_legend_checkbox, message).to_be_checked()
        expect(self.style_radio(mode), message).to_be_checked()
