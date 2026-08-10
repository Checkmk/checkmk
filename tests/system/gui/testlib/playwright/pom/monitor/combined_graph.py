#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import override

from playwright.sync_api import expect, Locator
from playwright.sync_api import TimeoutError as PWTimeoutError

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.graphing.graph_accessor import GraphAccessor
from tests.system.gui.testlib.playwright.pom.graphing.graph_surfaces import GraphContainment
from tests.system.gui.testlib.playwright.pom.graphing.timeseries_graph import GraphPanel
from tests.system.gui.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class CombinedGraphsServiceSearch(CmkPage):
    """Represent the page `Combined graphs - Service search`."""

    page_title = "Combined graphs \\(.*\\) - Service search"

    @override
    def navigate(self) -> None:
        raise NotImplementedError(
            f"Navigate method for '{self.page_title}' is not implemented. The navigation to "
            "this page can vary based on the filters applied on the 'Service Search' page.",
        )

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is 'Combined graphs - Service search' page")
        self.main_area.check_page_title(re.compile(self.page_title))

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def panels(self) -> Locator:
        return GraphAccessor(self).graph_root(GraphContainment.PAGE_DIRECT)

    @property
    def global_time_picker(self) -> Locator:
        return self.main_area.locator(".graphing-global-time-picker")

    def _panel(self, root: Locator) -> GraphPanel:
        return GraphPanel(root, self.page, self.main_area)

    def panel(self, graph_title: str) -> GraphPanel:
        return self._panel(self.panels.filter(has_text=graph_title))

    def all_panels(self) -> list[GraphPanel]:
        # ``.count()`` does not auto-wait, so this is only correct after ``wait_until_rendered``.
        return [self._panel(self.panels.nth(index)) for index in range(self.panels.count())]

    def wait_until_rendered(self) -> None:
        """Waits for the first card's plot: the group assigns them all in one tick."""
        self._panel(self.panels.first).graph.canvas.wait_for(state="visible")

    @property
    def broken_graph(self) -> Locator:
        """The notices shown in place of the cards that could not be loaded.

        One per unloadable card, plus a standalone one when a first load produced no card
        to sit over - so this is scoped to the group and not capped at a single element.
        """
        return self.main_area.locator(".graphing-graph-notice--error")

    def check_graph(self, graph_title: str) -> None:
        canvas = self.panel(graph_title).graph.canvas
        try:
            expect(canvas).to_be_attached()
            canvas.scroll_into_view_if_needed()
            expect(canvas).to_be_visible()
        except (AssertionError, PWTimeoutError) as exc:
            exc.add_note(f"Could not find graph: '{graph_title}' on page: '{self.page_title}'!")
            raise exc
