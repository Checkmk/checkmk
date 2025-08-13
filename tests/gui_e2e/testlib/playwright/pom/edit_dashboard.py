#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from typing import override

from playwright.sync_api import expect

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.dashboard import BaseDashboard
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class EditDashboard(CmkPage):
    """Represent 'Edit dashboard' page.

    To navigate: '<Customized Dashboard> -> Dashboard -> Edit dashboard'.
    """

    page_title = "Edit dashboard"

    def __init__(
        self,
        dashboard: BaseDashboard,
        navigate_to_page: bool = True,
        contain_filter_sidebar: bool = False,
        timeout_assertions: int | None = None,
        timeout_navigation: int | None = None,
    ) -> None:
        self.dashboard = dashboard
        super().__init__(
            dashboard.page,
            navigate_to_page,
            contain_filter_sidebar,
            timeout_assertions,
            timeout_navigation,
        )

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)

    @override
    def navigate(self) -> None:
        self.dashboard.main_area.click_item_in_dropdown_list("Dashboard", "Properties")

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def save_and_go_to_dashboard(self, validate_dashboard_page: bool = False) -> None:
        self.main_area.get_suggestion("Save & go to dashboard").click()
        if validate_dashboard_page:
            self.dashboard.validate_page()
        else:
            self.page.wait_for_load_state("load")

    def expand_section(self, section_name: str) -> None:
        section = self.main_area.locator("table.nform", has_text=section_name)

        if "closed" in (section.get_attribute("class") or ""):
            section.click()

        expect(
            section,
            message=f"Section '{section_name}' is not expanded",
        ).to_contain_class("open")

    def select_required_context_filter(self, filter_name: str) -> None:
        self.main_area.locator(
            "select#dashboard_p_mandatory_context_filters_unselected"
        ).select_option(filter_name)
        self.main_area.locator("div#dashboard_d_mandatory_context_filters a.control.add").click()

        expect(
            self.main_area.locator("select#dashboard_p_mandatory_context_filters_selected"),
            message=f"Filter '{filter_name}' is not selected",
        ).to_have_text(filter_name)
