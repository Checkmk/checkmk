#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Page objects for the forecast graph surface (Pro+).

Forecast graphs are pagetype visuals reached through the Customize menu. The surface
renders the legacy graph unconditionally and the engine's ``cmk-graph-group`` only when
the request carries ``vue-graphing-enabled``, so which one a caller means is an explicit
choice: `ForecastGraph`'s ``engine`` flag and the accessors matching it.
"""

import logging
import re
from typing import override
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from playwright.sync_api import Locator, Page

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.graphing.graph_accessor import GraphAccessor
from tests.system.gui.testlib.playwright.pom.graphing.graph_surfaces import GraphContainment
from tests.system.gui.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)

# Nothing in the product emits this, so the engine is only reachable by adding it ourselves.
_ENGINE_REQUEST_VAR = "vue-graphing-enabled"

# Matches both variants `GraphGroup.vue` renders: over a panel, and standalone.
_ERROR_NOTICE_SELECTOR = ".graphing-graph-notice--error"


def _with_engine_enabled(url: str) -> str:
    """Return `url` carrying the engine's request variable."""
    parts = urlsplit(url)
    # Blank values are kept: dropping them would rewrite the URL the listing linked to.
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query[_ENGINE_REQUEST_VAR] = "1"
    return urlunsplit(parts._replace(query=urlencode(query)))


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
        engine: reload with the engine enabled once reached.
        navigate_to_page: navigate on construction, as `CmkPage` does.
    """

    def __init__(
        self, page: Page, name: str, *, engine: bool = False, navigate_to_page: bool = True
    ) -> None:
        self.name = name
        self.page_title = name
        self._engine = engine
        super().__init__(page=page, navigate_to_page=navigate_to_page)

    @override
    def navigate(self) -> None:
        logger.info("Navigate to forecast graph '%s'", self.name)
        forecast_graphs = ForecastGraphList(self.page)
        forecast_graphs.get_link(self.name).click()
        self.validate_page()
        if self._engine:
            # Through the listing first, so the graph is known to be there before the
            # variable is added to the URL it linked to.
            logger.info("Reload forecast graph '%s' with the engine enabled", self.name)
            self.goto(_with_engine_enabled(self.page.url))
            self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is forecast graph '%s'", self.name)
        self.page.wait_for_url(url=re.compile(re.escape("forecast_graph.py")), wait_until="load")

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def graph_container(self) -> Locator:
        """Return the container scoping the legacy forecast graph on this page."""
        return GraphAccessor(self).container(GraphContainment.PAGE_DIRECT)

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
