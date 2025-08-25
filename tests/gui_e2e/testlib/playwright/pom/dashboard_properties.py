#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from enum import StrEnum
from typing import override

from playwright.sync_api import expect, Page

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.custom_dashboard import CustomDashboard
from tests.gui_e2e.testlib.playwright.pom.dashboard import BaseDashboard
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class DashboardProperties(CmkPage):
    page_title: str

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def save_and_go_to_dashboard(self) -> None:
        self.main_area.get_suggestion("Save & go to dashboard").click()

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


class EditDashboard(DashboardProperties):
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
    def navigate(self) -> None:
        self.dashboard.main_area.click_item_in_dropdown_list("Dashboard", "Properties")


class SpecificObjectType(StrEnum):
    NO_RESTRICTIONS = "No restrictions to specific objects"
    RESTRICT_TO_A_SINGLE_HOST = "Restrict to a single host"
    MANUAL_RESTRICTIONS = "Configure restrictions manually"


class CreateDashboard(DashboardProperties):
    """Represent 'Create dashboard' page.

    To navigate: 'Customize > Dashboards > Add dashboard'.
    """

    page_title = "Create dashboard"

    def __init__(
        self,
        page: Page,
        navigate_to_page: bool = True,
        contain_filter_sidebar: bool = False,
        timeout_assertions: int | None = None,
        timeout_navigation: int | None = None,
        specific_object_type: SpecificObjectType | None = None,
    ) -> None:
        self.specific_object_type = specific_object_type
        super().__init__(
            page,
            navigate_to_page,
            contain_filter_sidebar,
            timeout_assertions,
            timeout_navigation,
        )

    @override
    def navigate(self) -> None:
        self.main_menu.customize_menu("Dashboards").click()
        self.main_area.get_suggestion("Add dashboard").click()

        # We are not on a DashboardProperties page, but "Create dashboard" title is already
        # there. So, we just validate it.
        self.main_area.check_page_title(self.page_title)

        if self.specific_object_type is not None:
            self.main_area.locator("table.nform tr", has_text="Specific objects").locator(
                "span.selection"
            ).click()
            self.main_area.locator("ul#select2-single_infos_sel-results").locator(
                "li", has_text=self.specific_object_type
            ).click()

        self.main_area.get_suggestion("Continue").click()

        self.validate_page()

    def create_custom_dashboard(self, dashboard_name: str) -> CustomDashboard:
        self.main_area.get_input("general_p_name").fill(dashboard_name.lower().replace(" ", "_"))
        self.main_area.get_input("general_p_title").fill(dashboard_name)
        self.main_area.get_suggestion("Save & go to dashboard").click()

        return CustomDashboard(self.page, dashboard_name, navigate_to_page=False)
