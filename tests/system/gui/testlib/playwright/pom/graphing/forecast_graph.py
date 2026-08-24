#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Page objects for the forecast graph surface (Pro+).

Forecast graphs are pagetype visuals reached through the Customize menu. The surface
renders through the graph engine, mounting a ``cmk-graph-group``.
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

# Matches both variants `GraphGroup.vue` renders: over a panel, and standalone.
_ERROR_NOTICE_SELECTOR = ".graphing-graph-notice--error"


class ForecastGraphList(CmkPage):
    """The 'Forecast graphs' listing page (Customize menu)."""

    page_title: str = "Forecast graphs"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        self.main_menu.customize_menu(self.page_title).click()
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.page.wait_for_url(url=re.compile(re.escape("forecast_graphs.py")), wait_until="load")
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()


class ForecastGraph(CmkPage):
    """The display page of a single saved forecast graph.

    Args:
        page: the browser page to drive.
        name: the title the graph is listed under.
        navigate_to_page: navigate on construction, as `CmkPage` does.
    """

    def __init__(self, page: Page, name: str, *, navigate_to_page: bool = True) -> None:
        self.name = name
        self.page_title = name
        super().__init__(page=page, navigate_to_page=navigate_to_page)

    @override
    def navigate(self) -> None:
        logger.info("Navigate to forecast graph '%s'", self.name)
        forecast_graphs = ForecastGraphList(self.page)
        forecast_graphs.get_link(self.name).click()
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is forecast graph '%s'", self.name)
        self.page.wait_for_url(url=re.compile(re.escape("forecast_graph.py")), wait_until="load")

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def engine_graph_group(self) -> Locator:
        """The group the engine mounts for this graph."""
        return GraphAccessor(self).engine_graph_group(GraphContainment.PAGE_DIRECT)

    @property
    def engine_panels(self) -> Locator:
        """Every graph the engine drew. Anchor the count before addressing one by index."""
        return GraphAccessor(self).graph_root(GraphContainment.PAGE_DIRECT)

    @property
    def error_notices(self) -> Locator:
        """The engine's error state, standing in for a graph it could not draw."""
        return self.engine_graph_group.locator(_ERROR_NOTICE_SELECTOR)
