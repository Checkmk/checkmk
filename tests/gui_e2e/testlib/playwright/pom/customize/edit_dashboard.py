#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from dataclasses import dataclass
from typing import override

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.gui_e2e.testlib.playwright.pom.sidebar.create_dashboard_sidebar import (
    DashboardType,
)


@dataclass
class NewDashboardCharacteristics:
    """Characteristics for creating a new dashboard.

    Attributes:
        name: The name of the dashboard.
        dashboard_type: The type of dashboard to create.
        unique_id: Optional custom unique identifier for the dashboard.
    """

    name: str
    dashboard_type: DashboardType | None = None
    unique_id: str | None = None


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
