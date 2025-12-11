#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal, overload, override

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.pom.monitor.custom_dashboard import CustomDashboard
from tests.gui_e2e.testlib.playwright.pom.sidebar.widget_wizard_sidebar import (
    BaseWidgetWizard,
    MetricsAndGraphsWidgetWizard,
    WidgetType,
    WidgetWizardMode,
)


class EmptyDashboard(CustomDashboard):
    """Represents a new dashboard that does not have any widget yet.

    To navigate: 'Customize > Dashboards > Add dashboard > {complete the creation process}'.
    """

    @override
    def _validate_main_content(self) -> None:
        """Validate that main content of the dashboard is displayed.

        In an empty dashboard, the region to add a new widget is displayed instead of the
        dashboard container.
        """
        expect(
            self.add_widget_buttons_container, message=f"Dashboard '{self.page_title}' is not empty"
        ).to_be_visible()

    @property
    def add_widget_buttons_container(self) -> Locator:
        """Locator property for the region to add a new widget in an empty dashboad."""
        return self.main_area.locator().get_by_role("region", name="Add widget")

    def _get_button_to_add_widget_by_type(self, widget_type: WidgetType) -> Locator:
        """Get the button to add a new widget.

        It gets the button from the central area of an empty dashboard.

        Args:
            widget_type: the widget type of the button.

        Returns:
            The locator of the button to add the given widget type.
        """
        return self.add_widget_buttons_container.get_by_role("link", name=widget_type)

    @overload
    def open_add_widget_sidebar(
        self, widget_type: Literal[WidgetType.METRICS_AND_GRAPHS]
    ) -> MetricsAndGraphsWidgetWizard: ...

    @overload
    def open_add_widget_sidebar(self, widget_type: WidgetType) -> BaseWidgetWizard: ...

    @override
    def open_add_widget_sidebar(self, widget_type: WidgetType) -> BaseWidgetWizard:
        """Open the sidebar to add a new widget.

        Args:
            widget_type: the widget type for which the sidebar will be open.

        Returns:
            The `BaseWidgetWizard` object of the open sidebar.
        """
        self._get_button_to_add_widget_by_type(widget_type).click()
        wizard = widget_type.get_wizard(WidgetWizardMode.ADD_WIDGET, self.page)
        wizard.expect_to_be_visible()
        return wizard
