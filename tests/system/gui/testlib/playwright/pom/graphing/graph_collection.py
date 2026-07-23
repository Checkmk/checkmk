#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Navigation page-objects for the graph collection surface (Pro+).

Graph collections are pagetype visuals reached through the Customize menu. A
collection renders several graphs in sequence on one page. This module provides
the navigation foundation only; assertions against the rendered graphs belong to
the graph test suites once the new engine renders on the surface.
"""

import logging
import re
from typing import override

from playwright.sync_api import Locator, Page

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.graphing.graph_accessor import GraphAccessor
from tests.system.gui.testlib.playwright.pom.graphing.graph_surfaces import GraphContainment
from tests.system.gui.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


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

    def graph_containers(self) -> Locator:
        """Locator matching *every* graph in the collection (multiple elements).

        A single-element action/assertion on it raises Playwright strict-mode. To
        act on all, anchor the count first — ``expect(loc).to_have_count(n)``
        auto-waits for every graph to render (``.all()`` / ``.count()`` only
        snapshot) — then iterate ``loc.all()`` or ``loc.nth(i)``.
        """
        return GraphAccessor(self).container(GraphContainment.PAGE_DIRECT)
