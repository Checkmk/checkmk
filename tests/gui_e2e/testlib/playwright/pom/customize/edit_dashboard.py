#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.monitor.empty_dashboard import EmptyDashboard
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.gui_e2e.testlib.playwright.pom.sidebar.base_sidebar import SidebarHelper


class DashboardType(StrEnum):
    """Enumeration of available dashboard types."""

    UNRESTRICTED = "Unrestricted"
    SPECIFIC_HOST = "Specific host"
    CUSTOM = "Custom"


@dataclass
class NewDashboardCaracteristics:
    """Characteristics for creating a new dashboard.

    Attributes:
        name: The name of the dashboard.
        dashboard_type: The type of dashboard to create.
        unique_id: Optional custom unique identifier for the dashboard.
    """

    name: str
    dashboard_type: DashboardType | None = None
    unique_id: str | None = None


class CreateDashboardSidebar(SidebarHelper):
    """Class that represents the sidebar to create a new dashboard.

    To navigate: 'Customize > Dashboards > Add dashboard'.
    """

    sidebar_title = "Create dashboard"

    @property
    @override
    def _sidebar_locator(self) -> Locator:
        """Locator property for the main area of the sidebar."""
        return self._iframe_locator.get_by_role("dialog", name=self.sidebar_title)

    @property
    def create_button(self) -> Locator:
        """Locator property for the button to create the dashboard."""
        return self.locator().get_by_role("button", name="Create")

    @property
    def name_input(self) -> Locator:
        """Locator property for the input to set the name of the new dashboard."""
        return self.locator().get_by_role("textbox", name="Enter name")

    @property
    def automatic_unique_id_checkbox(self) -> Locator:
        """Locator property for the checkbox to automatically create a unique ID."""
        return self.locator().get_by_role("checkbox", name="Automatically create unique ID")

    @property
    def unique_id_input(self) -> Locator:
        """Locator property for the input to set a custom unique ID."""
        return self.locator().get_by_role("textbox", name="Add unique ID")

    def _get_dashboard_type_button(self, dashboard_type: DashboardType) -> Locator:
        """Get the locator for the button to select a specific dashboard type.

        Args:
            dashboard_type: the type of dashboard to select.

        Returns:
            Locator for the dashboard type button.
        """
        return self.locator().get_by_role("button", name=dashboard_type)

    def expect_page_title(self) -> None:
        """Verify that the sidebar title is visible."""
        expect(
            self.sidebar_title_locator,
            message=f"'{self.sidebar_title}' sidebar title is not present",
        ).to_be_visible()

    def fill_unique_id(self, unique_id: str) -> None:
        """Fill in a custom unique ID for the dashboard.

        Args:
            unique_id: the custom unique identifier for the dashboard.
        """
        self.automatic_unique_id_checkbox.uncheck()
        self.unique_id_input.fill(unique_id)

    def expect_auto_generated_unique_id_to_be_populated(self) -> None:
        """Verify that an auto-generated unique ID has been populated."""
        auto_generated_unique_id_checkbox_label = "Automatically create unique ID"
        expect(
            self.locator(
                "div.field-component",
                has_text=auto_generated_unique_id_checkbox_label,
            ),
            message="Auto-generated unique ID label is not populated",
        ).to_have_text(re.compile(rf"{auto_generated_unique_id_checkbox_label}: \w+"))


class FilterConfigurationSidebar(SidebarHelper):
    """Class that represents the sidebar to filter a dashboard.

    To navigate: '{within any dasboard} > Filter'.
    """

    sidebar_title = "Filter configuration"

    @property
    @override
    def _sidebar_locator(self) -> Locator:
        """Locator property for the main area of the sidebar."""
        return self._iframe_locator.get_by_role("dialog", name="Dashboard filter")

    @property
    @override
    def sidebar_title_locator(self) -> Locator:
        """Locator property for the sidebar title."""
        return self.locator().get_by_text(self.sidebar_title)

    @property
    def close_filter_configuration_button(self) -> Locator:
        """Locator property for the button to close the filter configuration."""
        return self.locator().get_by_role("button", name="Close filter configuration")


class EditDashboards(CmkPage):
    """Represent 'Edit dashboards' page.

    To navigate: 'Customize > Dashboards'.
    """

    page_title = "Edit dashboards"

    @override
    def validate_page(self) -> None:
        self.page.wait_for_url(url=re.compile("edit_dashboards.py"), wait_until="load")
        self.main_area.check_page_title(self.page_title)

    @override
    def navigate(self) -> None:
        self.main_menu.customize_menu("Dashboards").click()
        self.validate_page()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        mapping = DropdownListNameToID()
        setattr(mapping, "Dashboards", "menu_dashboards")
        return mapping

    @property
    def _customized_dashboards_table(self) -> Locator:
        """Locator property for the customized dashboards table."""
        return self.main_area.locator(
            "//h3[@class='table'][text()='Customized']/following-sibling::table[1]"
        )

    @property
    def _built_in_dashboards_table(self) -> Locator:
        """Locator property for the built-in dashboards table."""
        return self.main_area.locator(
            "//h3[@class='table'][text()='Built-in']/following-sibling::table[1]"
        )

    def navigate_to_dashboard(self, dashboard_name: str, *, is_customized: bool) -> None:
        """Navigate to a specific dashboard by clicking on it.

        Args:
            dashboard_name: the name of the dashboard to navigate to.
            is_customized: whether the dashboard is customized (True) or built-in (False).
        """
        table = (
            self._customized_dashboards_table if is_customized else self._built_in_dashboards_table
        )
        table.get_by_role("link", name=dashboard_name, exact=True).click()

    def create_new_dashboard(
        self, dashboard_caracteristics: NewDashboardCaracteristics
    ) -> EmptyDashboard:
        """Create a new dashboard with specified characteristics.

        Args:
            dashboard_caracteristics: the characteristics of the new dashboard including
                name, type, and unique ID.

        Returns:
            EmptyDashboard instance representing the newly created dashboard.
        """
        self.main_area.click_item_in_dropdown_list("Dashboards", "Add dashboard", exact=True)
        self.page.wait_for_url(
            url=re.compile(quote_plus("dashboard.py?mode=create")), wait_until="load"
        )

        create_dashboard_sidebar = CreateDashboardSidebar(self.page)

        # Select dashboard type if provided
        if dashboard_caracteristics.dashboard_type is not None:
            create_dashboard_sidebar._get_dashboard_type_button(
                dashboard_caracteristics.dashboard_type
            ).click()

        # Fill in dashboard name
        create_dashboard_sidebar.name_input.fill(dashboard_caracteristics.name)

        # Fill in unique ID if provided
        if dashboard_caracteristics.unique_id is not None:
            create_dashboard_sidebar.fill_unique_id(dashboard_caracteristics.unique_id)

        else:
            create_dashboard_sidebar.expect_auto_generated_unique_id_to_be_populated()

        create_dashboard_sidebar.create_button.click()

        return EmptyDashboard(
            self.page,
            page_title=dashboard_caracteristics.name,
            navigate_to_page=False,
        )

    def delete_dashboard(self, dashboard_name: str) -> None:
        """Delete a dashboard by name and verify deletion.

        Args:
            dashboard_name: the name of the dashboard to delete.
        """
        custom_dashboard_link = (
            self.main_area.locator().get_by_role("link", name=dashboard_name, exact=True).first
        )
        custom_dashboard_row = self.main_area.locator("tr", has=custom_dashboard_link)
        custom_dashboard_row.get_by_role("link", name="Delete").click()
        self.main_area.get_confirmation_popup_button("Delete").click()

        expect(
            self.main_area.locator("div.success"),
            message=f"Dashboard '{self.page_title}' is not deleted",
        ).to_have_text("Your dashboard has been deleted.")
