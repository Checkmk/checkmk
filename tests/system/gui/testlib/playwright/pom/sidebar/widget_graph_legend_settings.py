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

SHOW_LEGEND_LABEL = "Show graph legend"


class GraphLegendMode(StrEnum):
    """What a graph widget shows as its legend."""

    NO_LEGEND = "No legend"
    COMPACT = "Compact"
    EXTENDED = "Extended"


# The modes offered as a style once the legend is shown, by the label of their radio button.
LEGEND_STYLES = (GraphLegendMode.COMPACT, GraphLegendMode.EXTENDED)


class WidgetGraphLegendSettings:
    """The 'Legend' row of a graph widget wizard.

    The row is part of the 'Additional graph options' panel, which starts out collapsed: open
    it first, e.g. with `MetricsAndGraphsWidgetWizard.expand_collapsed_panels`.

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
    def show_legend_checkbox(self) -> Locator:
        return self._row.get_by_role("checkbox", name=SHOW_LEGEND_LABEL, exact=True)

    @property
    def style_radios(self) -> Locator:
        """Every legend style the row offers, present only while the legend is shown."""
        return self._row.get_by_role("radio")

    def style_radio(self, style: GraphLegendMode) -> Locator:
        return self._row.get_by_role("radio", name=style, exact=True)

    def select_mode(self, mode: GraphLegendMode) -> None:
        if mode is GraphLegendMode.NO_LEGEND:
            self.show_legend_checkbox.uncheck()
            return
        self.show_legend_checkbox.check()
        self.style_radio(mode).check()

    def expect_mode(self, mode: GraphLegendMode, message: str) -> None:
        """Wait for the row to show the mode as picked."""
        if mode is GraphLegendMode.NO_LEGEND:
            expect(self.show_legend_checkbox, message).not_to_be_checked()
            expect(self.style_radios, message).to_have_count(0)
            return
        expect(self.show_legend_checkbox, message).to_be_checked()
        expect(self.style_radio(mode), message).to_be_checked()
