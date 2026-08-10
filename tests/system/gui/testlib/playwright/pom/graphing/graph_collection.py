#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Page objects for the graph collection surface (Pro+).

Graph collections are pagetype visuals reached through the Customize menu. A
collection renders one slot per graph it holds, each mounting a graph group of its own.
"""

import logging
import re
from typing import override

from playwright.sync_api import Locator, Page

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.graphing.graph_accessor import (
    ENGINE_GRAPH_GROUP_SELECTOR,
    ENGINE_GRAPH_PANEL_SELECTOR,
    GraphAccessor,
)
from tests.system.gui.testlib.playwright.pom.graphing.graph_surfaces import GraphContainment
from tests.system.gui.testlib.playwright.pom.graphing.timeseries_graph import GraphPanel
from tests.system.gui.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)

_SLOT_SELECTOR = "table.graph_collection td.graph"
# A class fragment, as the server combines it with others.
_BROKEN_GRAPH_SELECTOR = "div[class*='brokengraph']"
_ERROR_NOTICE_SELECTOR = ".graphing-graph-notice--error"
_SKELETON_SELECTOR = ".graphing-graph-skeleton"
_PLOT_SELECTOR = f"{ENGINE_GRAPH_PANEL_SELECTOR} canvas[role='img']"
# The group reports itself loaded once its first fetch resolved, successfully or not.
_LOADED_GROUP_SELECTOR = f"{ENGINE_GRAPH_GROUP_SELECTOR}[aria-busy='false']"


class GraphCollectionList(CmkPage):
    """The 'Graph collections' listing page (Customize menu)."""

    page_title: str = "Graph collections"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        self.main_menu.customize_menu(self.page_title).click()
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.page.wait_for_url(url=re.compile(re.escape("graph_collections.py")), wait_until="load")
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()


class GraphCollection(CmkPage):
    """The display page of a single graph collection."""

    def __init__(self, page: Page, name: str, navigate_to_page: bool = True) -> None:
        self.name = name
        self.page_title = name
        super().__init__(page=page, navigate_to_page=navigate_to_page)

    @override
    def navigate(self) -> None:
        logger.info("Navigate to graph collection '%s'", self.name)
        graph_collections = GraphCollectionList(self.page)
        graph_collections.get_link(self.name).click()
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is graph collection '%s'", self.name)
        self.page.wait_for_url(url=re.compile(re.escape("graph_collection.py")), wait_until="load")

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def slots(self) -> Locator:
        """One cell per graph the collection holds."""
        return self.main_area.locator(_SLOT_SELECTOR)

    @property
    def slots_holding_a_graph(self) -> Locator:
        """The slots the engine mounted a graph into.

        Matched per slot, so a slot left empty is a failure of that slot rather than one graph
        of a neighbour standing in for it.
        """
        return self.main_area.locator(f"{_SLOT_SELECTOR}:has({_PLOT_SELECTOR})")

    @property
    def slots_reporting_loaded(self) -> Locator:
        """The slots whose graph finished loading, whether its data arrived or not."""
        return self.main_area.locator(f"{_SLOT_SELECTOR}:has({_LOADED_GROUP_SELECTOR})")

    @property
    def drawn_plots(self) -> Locator:
        """The plots on screen across the collection, one per graph that drew itself."""
        return self.main_area.locator(f"{_SLOT_SELECTOR} {_PLOT_SELECTOR}:visible")

    def engine_group(self, index: int) -> Locator:
        """The graph group mounted in the slot at `index`."""
        return GraphAccessor(self).engine_graph_group(
            GraphContainment.PAGE_DIRECT, within=self.slots.nth(index)
        )

    def panels(self, index: int) -> Locator:
        """The graphs the group in the slot at `index` rendered.

        Scoped to the slot, so a group that resolved no graph is a failure of that slot rather
        than an index shifted onto a neighbour's graph.
        """
        return GraphAccessor(self).graph_root(
            GraphContainment.PAGE_DIRECT, within=self.slots.nth(index)
        )

    def panel(self, index: int) -> GraphPanel:
        return GraphPanel(self.panels(index).first, self.page, self.main_area)

    @property
    def skeletons(self) -> Locator:
        """The placeholders standing in for the graphs while their first fetch is pending."""
        return self.main_area.locator(_SKELETON_SELECTOR)

    @property
    def broken_graphs(self) -> Locator:
        """The boxes the server renders in place of graphs it cannot resolve."""
        return self.main_area.locator(_BROKEN_GRAPH_SELECTOR)

    @property
    def error_notices(self) -> Locator:
        """The failure pills the engine shows for graphs whose data did not arrive."""
        return self.main_area.locator(_ERROR_NOTICE_SELECTOR)
