#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import override

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

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

    def _graph_with_timeranges_container(self, graph_title: str) -> Locator:
        return self.main_area.locator(
            f"div[class='graph_with_timeranges']:has(div[class='title']:text-is('{graph_title}'))"
        )

    def graph(self, graph_title: str) -> Locator:
        container = self._graph_with_timeranges_container(graph_title)
        expect(container).to_be_attached()
        return container.locator("div[class='graph'] >> canvas")

    def timerange_graph(self, graph_title: str, timerange_name: str) -> Locator:
        return self._graph_with_timeranges_container(graph_title).locator(
            f"div[class*='graph']:has-text('{timerange_name}') >> canvas"
        )

    @property
    def broken_graph(self) -> Locator:
        return self.main_area.locator("div[class*='brokengraph']")

    def check_graph_with_timeranges(self, graph_title: str) -> None:
        graph = self.graph(graph_title)
        expect(graph).to_be_attached()
        graph.scroll_into_view_if_needed()
        expect(graph).to_be_visible()
        timeranges_list = [
            "The last 4 hours",
            "The last 25 hours",
            "The last 8 days",
            "The last 35 days",
            "The last 400 days",
        ]
        for timerange in timeranges_list:
            timerange_graph = self.timerange_graph(graph_title, timerange)
            expect(timerange_graph).to_be_attached()
            timerange_graph.scroll_into_view_if_needed()
            expect(timerange_graph).to_be_visible()
