#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class AllAggregations(CmkPage):
    """Represents page `Monitor -> Business Intelligence -> All aggregations`"""

    page_title: str = "All aggregations"

    dropdown_buttons: list[str] = [
        "Commands",
        "BI Aggregations",
        "Export",
        "Display",
        "Help",
    ]

    links: list[str] = [
        "Acknowledge problems",
        "Schedule downtime",
        "Filter",
        "Show checkboxes",
    ]

    @override
    def navigate(self) -> None:
        """Instructions to navigate to `Monitor -> Business Intelligence -> All aggregations` page."""
        logger.info("Navigate to '%s' page", self.page_title)
        self.main_menu.monitor_menu(self.page_title).click()
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.page.wait_for_url(url=re.compile(quote_plus("view_name=aggr_all")), wait_until="load")
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def _aggregation_group(self, group_name: str) -> Locator:
        return self.main_area.locator("table.data").filter(has_text=group_name)

    @property
    def hosts_aggregation_group(self) -> Locator:
        return self._aggregation_group(group_name="Hosts")

    def hosts_aggregation_row(self, index: int) -> "_HostsAggregationRow":
        """Return a locator corresponding to a row of aggregations.

        The aggregation / row is specific to the aggregation group: 'Hosts'.
        """
        return self._HostsAggregationRow(self.hosts_aggregation_group, index)

    class _HostsAggregationRow:
        """Represents a single data row in the All Aggregations table."""

        def __init__(self, aggregation_group_locator: Locator, index: int) -> None:
            """Initialize HostsAggregationRow with its row index."""
            self._aggregation_group = aggregation_group_locator
            self._index = index
            self._row_locator = self._aggregation_group.locator("tr.data").nth(self._index)

        @property
        def locator(self) -> Locator:
            return self._row_locator

        @property
        def _state_cell(self) -> Locator:
            return self._row_locator.locator("td.state")

        @property
        def _tree_cell(self) -> Locator:
            """Return the locator for the tree container within the 'Tree' column."""
            return self._row_locator.locator("td.aggrtree")

        @property
        def _hosts_cell(self) -> Locator:
            return self._row_locator.locator("td").last

        @property
        def visualize_icon(self) -> Locator:
            return self._row_locator.get_by_role("link", name="Visualize this aggregation")

        @property
        def show_only_icon(self) -> Locator:
            return self._row_locator.get_by_role("link", name="Show only this aggregation")

        @property
        def analyse_availability_icon(self) -> Locator:
            return self._row_locator.get_by_role(
                "link", name="Analyse availability of this aggregation"
            )

        @property
        def state(self) -> str:
            """Return the status of the aggregation as seen within the 'State' column."""
            expect(
                loc_ := self._state_cell, message="Aggregation state is not visible!"
            ).to_be_visible()
            return loc_.inner_text()

        @property
        def _tree_container(self) -> Locator:
            """Return the locator for the tree container within the 'Tree' column."""
            return self._tree_cell.locator("div.bi_tree_container")

        @property
        def tree_name(self) -> str:
            """Return the aggregation name as seen in the 'Tree' column."""
            expect(
                loc_ := self._tree_container.locator("span.content.name").first,
                message="Aggregation-tree is not visible!",
            ).to_be_visible()
            return loc_.inner_text()

        @property
        def host_link(self) -> Locator:
            """Return the locator for the host link in the 'Hosts' column."""
            return self._hosts_cell.get_by_role("link")
