#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from typing import override

from playwright.sync_api import expect, Locator, Page

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class ServicePage(CmkPage):
    """Represent 'Service' page.

    To navigate: 'Monitor > Overview > (All hosts > Host > Services of host) > Service
    """

    def __init__(
        self,
        page: Page,
        host_name: str,
        service_name: str,
        navigate_to_page: bool = True,
    ) -> None:
        self.host_name = host_name
        self.service_name = service_name
        self.page_title = f"Service {service_name}, {host_name}"
        super().__init__(page=page, navigate_to_page=navigate_to_page)

    @override
    def navigate(self) -> None:
        raise NotImplementedError("There are different ways to navigate to a Service page.")

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is %s page", self.page_title)
        expect(self.main_area.page_title_locator).to_contain_text(self.host_name)
        expect(self.main_area.page_title_locator).to_contain_text(self.service_name)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def row_content(self, row_name: str) -> Locator:
        return self.main_area.locator(f"tr:has(td.left:has-text('{row_name}'))").locator(
            "td:nth-child(2)"
        )

    def _graph_with_timeranges_container(self, graph_title: str) -> Locator:
        return self.main_area.locator().locator(
            "div[class='graph_with_timeranges']:has(div[class='title'])",
            has_text=graph_title,
        )

    def graph(self, graph_title: str) -> Locator:
        container = self._graph_with_timeranges_container(graph_title)
        expect(container).to_be_attached()
        return container.locator("div[class='graph'] >> canvas")

    @property
    def broken_graph(self) -> Locator:
        return self.main_area.locator("div[class*='brokengraph']")
