#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from enum import StrEnum
from typing import override

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.pom.sidebar.base_sidebar import SidebarHelper


class DashboardType(StrEnum):
    """Enumeration of available dashboard types."""

    UNRESTRICTED = "Unrestricted"
    SPECIFIC_HOST = "Specific host"
    CUSTOM = "Custom"


class BaseDashboarCreationSidebar(SidebarHelper):
    """Base class to create or clone a dashboard.

    They both have many attributes in common.
    """

    @property
    @override
    def _sidebar_locator(self) -> Locator:
        """Locator property for the main area of the sidebar."""
        return self._iframe_locator.get_by_role("dialog", name=self.sidebar_title)

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

    def expect_auto_generated_unique_id_to_be_populated(self, expected_value: str) -> None:
        """Verify that an auto-generated unique ID has been populated."""
        auto_generated_unique_id_checkbox_label = "Automatically create unique ID"

        expect(
            self.automatic_unique_id_checkbox,
            message=f"'{auto_generated_unique_id_checkbox_label}' checkbox is not checked",
        ).to_be_checked()
        expect(
            self.locator(
                "div.field-component",
                has_text=auto_generated_unique_id_checkbox_label,
            ),
            message="Auto-generated unique ID label is not populated",
        ).to_have_text(
            re.compile(rf"{auto_generated_unique_id_checkbox_label}: {expected_value}(_\d)?$")
        )


class CreateDashboardSidebar(BaseDashboarCreationSidebar):
    """Class that represents the sidebar to create a new dashboard.

    To navigate: 'Customize > Dashboards > Add dashboard'.
    """

    sidebar_title = "Create dashboard"

    @property
    def create_button(self) -> Locator:
        """Locator property for the button to create the dashboard."""
        return self.locator().get_by_role("button", name="Create")

    def _get_dashboard_type_button(self, dashboard_type: DashboardType) -> Locator:
        """Get the locator for the button to select a specific dashboard type.

        Args:
            dashboard_type: the type of dashboard to select.

        Returns:
            Locator for the dashboard type button.
        """
        return self.locator().get_by_role("button", name=dashboard_type)


class CloneDashboardSidebar(BaseDashboarCreationSidebar):
    """Class that represents the sidebar to create a new dashboard.

    To navigate: 'Customize > Dashboards > {any dashboard in the table} > clone button'.
    """

    sidebar_title = "Clone dashboard"

    @property
    def clone_button(self) -> Locator:
        """Locator property for the button to create the dashboard."""
        return self.locator().get_by_role("button", name="Clone")
