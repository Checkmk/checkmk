#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from typing import Literal, overload, override

from playwright.sync_api import expect, Locator, Page

from tests.gui_e2e.testlib.playwright.pom.monitor.dashboard import BaseDashboard
from tests.gui_e2e.testlib.playwright.pom.sidebar.widget_wizard_sidebar import (
    AddWidgetSidebar,
    BaseWidgetWizard,
    MetricsAndGraphsWidgetWizard,
    WidgetType,
    WidgetWizardMode,
)

logger = logging.getLogger(__name__)


class CustomDashboard(BaseDashboard):
    """Represents a custom dashboard.

    To navigate: 'Customize > Dashboards > {select any dashboard from 'customized' table}'.
    """

    def __init__(self, page: Page, page_title: str, navigate_to_page: bool = True):
        self.page_title = page_title
        super().__init__(page, navigate_to_page)

    @override
    def navigate(self) -> None:
        # Method level import to avoid circular import errors
        from tests.gui_e2e.testlib.playwright.pom.customize.edit_dashboard import EditDashboards

        logger.info("Navigate to '%s'", self.page_title)
        EditDashboards(self.page).navigate_to_dashboard(self.page_title, is_customized=True)
        self.validate_page()

    @override
    def validate_page(self) -> None:
        self.check_selected_dashboard_name()
        self._validate_main_content()

    def _validate_main_content(self) -> None:
        """Validate that main content of the dashboard is displayed."""
        expect(
            self.dashboard_container, message=f"Dashboard '{self.page_title}' is not loaded"
        ).to_be_visible()

    @overload
    def open_add_widget_sidebar(
        self, widget_type: Literal[WidgetType.METRICS_AND_GRAPHS]
    ) -> MetricsAndGraphsWidgetWizard: ...

    @overload
    def open_add_widget_sidebar(self, widget_type: WidgetType) -> BaseWidgetWizard: ...

    def open_add_widget_sidebar(self, widget_type: WidgetType) -> BaseWidgetWizard:
        """Open the sidebar to add a new widget.

        Args:
            widget_type: the widget type for which the sidebar will be open.

        Returns:
            The `BaseWidgetWizard` object of the open sidebar.
        """
        self.add_widget_button.click()
        add_widget_sidebar = AddWidgetSidebar(self.page)
        add_widget_sidebar.expect_to_be_visible()
        return add_widget_sidebar.open_widget_wizard(widget_type)

    @property
    def edit_widgets_button(self) -> Locator:
        """Locator property for the 'Edit widgets' button"""
        return self.main_area.locator().get_by_role("button", name="Edit widgets")

    @property
    def add_widget_button(self) -> Locator:
        """Locator property for the 'Add widget' button"""
        return self.main_area.locator().get_by_role("button", name="Add widget")

    @property
    def save_button(self) -> Locator:
        """Locator property for the 'Save' button"""
        return self.main_area.locator().get_by_role("button", name="Save")

    def enter_edit_widgets_mode(self) -> None:
        """Activate the mode to edit widgets of the dashboard"""
        self.edit_widgets_button.click()

    @overload
    def open_edit_widget_sidebar(
        self, widget_type: Literal[WidgetType.METRICS_AND_GRAPHS], widget_title: str
    ) -> MetricsAndGraphsWidgetWizard: ...

    @overload
    def open_edit_widget_sidebar(
        self, widget_type: WidgetType, widget_title: str
    ) -> BaseWidgetWizard: ...

    def open_edit_widget_sidebar(
        self, widget_type: WidgetType, widget_title: str
    ) -> BaseWidgetWizard:
        """Open the sidebar to edit a widget.

        Args:
            widget_type: the widget type for which the sidebar will be open.
            widget_title: the title of the widget to open the edit sidebar.

        Returns:
            The `BaseWidgetWizard` object of the open sidebar.
        """
        self.edit_widget_properties_button(widget_title).click()
        return widget_type.get_wizard(WidgetWizardMode.EDIT_WIDGET, self.page)
