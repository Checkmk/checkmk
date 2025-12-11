#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from enum import StrEnum
from typing import Literal, overload, override

from playwright.sync_api import Locator, Page

from tests.gui_e2e.testlib.playwright.dropdown import DropdownHelper, DropdownOptions
from tests.gui_e2e.testlib.playwright.pom.sidebar.base_sidebar import SidebarHelper


class AddWidgetSidebar(SidebarHelper):
    """Represents the sidebar to add a new widget to the dashboard.

    To navigate: '{within any customized dashboard} > Add widget'.
    """

    sidebar_title = "Add widget"

    @property
    @override
    def _sidebar_locator(self) -> Locator:
        """Locator property for the main area of the sidebar."""
        return self._iframe_locator.get_by_role("dialog", name="Add widget")

    def _get_button_to_add_widget_by_type(self, widget_type: WidgetType) -> Locator:
        """Get the button to add a new widget.

        Args:
            widget_type: the widget type of the button.

        Returns:
            The locator of the button to add the given widget type.
        """
        return self.locator().get_by_role("button", name=widget_type)

    @overload
    def open_widget_wizard(
        self, widget_type: Literal[WidgetType.METRICS_AND_GRAPHS]
    ) -> MetricsAndGraphsWidgetWizard: ...

    @overload
    def open_widget_wizard(self, widget_type: WidgetType) -> BaseWidgetWizard: ...

    def open_widget_wizard(self, widget_type: WidgetType) -> BaseWidgetWizard:
        """Open the wizard to add a new widget.

        Args:
            widget_type: the type of the widget that will be added.

        Returns:
            The `BaseWidgetWizard` object of the open sidebar.
        """
        self._get_button_to_add_widget_by_type(widget_type).click()
        wizard = widget_type.get_wizard(WidgetWizardMode.ADD_WIDGET, self.page)
        wizard.expect_to_be_visible()
        return wizard


class WidgetType(StrEnum):
    """Enumeration that defines the types of the widgets that can be added to a custom dashboard."""

    METRICS_AND_GRAPHS = "Metrics & graphs"

    @overload
    def get_wizard(  # type: ignore[misc] # https://github.com/python/mypy/issues/15456
        self: Literal[WidgetType.METRICS_AND_GRAPHS], wizard_mode: WidgetWizardMode, page: Page
    ) -> MetricsAndGraphsWidgetWizard: ...

    @overload
    def get_wizard(
        self: WidgetType, wizard_mode: WidgetWizardMode, page: Page
    ) -> BaseWidgetWizard: ...

    def get_wizard(self: WidgetType, wizard_mode: WidgetWizardMode, page: Page) -> BaseWidgetWizard:
        """Get the `BaseWidgetWizard` instance corresponding to the widget type.

        Args:
            page: the base page to initialize the `BaseWidgetWizard` object.

        Returns:
            The `BaseWidgetWizard` instance corresponding to the widget type
        """
        match self:
            case WidgetType.METRICS_AND_GRAPHS:
                return MetricsAndGraphsWidgetWizard(wizard_mode, page)
            case _:
                raise NotImplementedError(f"Widget wizard for '{self}' is not implemented.")


class ServiceMetricDropdownOptions(DropdownOptions):
    CPU_UTILIZATION = "CPU utilization"


class VisualizationType(StrEnum):
    """Enumeration to define the type of visualization that a widget could have."""

    GRAPH = "Graph"
    METRIC = "Metric"
    GAUGE = "Gauge"
    BARPLOT = "Barplot"
    SCATTERPLOT = "Scatterplot"
    TOP_LIST = "Top list"


class WidgetWizardMode(StrEnum):
    ADD_WIDGET = "Add widget"
    EDIT_WIDGET = "Edit widget"

    @property
    def wizard_dialog_name(self) -> str:
        match self:
            case WidgetWizardMode.ADD_WIDGET:
                return "Add widget to dashboard"
            case WidgetWizardMode.EDIT_WIDGET:
                return "Edit widget properties"


class BaseWidgetWizard(SidebarHelper):
    """Base class for widget wizard sidebar helpers"""

    def __init__(
        self, wizard_mode: WidgetWizardMode, page: Page, validate_sidebar: bool = True
    ) -> None:
        self._wizard_mode = wizard_mode
        super().__init__(page, validate_sidebar)

    @property
    @override
    def _sidebar_locator(self) -> Locator:
        """Locator property for the main area of the sidebar."""
        return self._iframe_locator.get_by_role("dialog", name=self._wizard_mode.wizard_dialog_name)


class MetricsAndGraphsWidgetWizard(BaseWidgetWizard):
    """Represents the widget wizard sidebar to configure 'Metrics & graphs' widget

    To navigate: '{within any customized dashboard} > Add widget > Metrics & graphs'.
    """

    sidebar_title = "Metrics & graphs"

    @property
    def _metric_selection_region(self) -> Locator:
        """Locator property of 'Host selection' region."""
        return self.locator().get_by_role("region", name="Metric selection")

    @property
    def _available_visualization_type_region(self) -> Locator:
        """Locator property of 'Available visualization type' region."""
        return self.locator().get_by_role("region", name="Available visualization type")

    @property
    def _service_metric_combobox(self) -> Locator:
        """Locator property of combobox to select the service metric of the widget."""
        return self._metric_selection_region.get_by_role("combobox", name="Select service metric")

    @property
    def _combobox_text_input(self) -> Locator:
        """Locator property of the text input to search a value in a combobox."""
        return self.locator().get_by_role("listbox").get_by_role("textbox")

    @property
    def next_step_visualization_button(self) -> Locator:
        """Locator property of 'Next step: Visualization' button."""
        return self.locator().get_by_role("button", name="Next step: Visualization")

    @property
    def add_and_place_widget_button(self) -> Locator:
        """Locator property of 'Add & place widget' button."""
        return self.locator().get_by_role("button", name="Add & place widget")

    def select_visualization_type(self, visualization_type: VisualizationType) -> None:
        """Select the type of visualization for the widget.

        Args:
            visualization_type: type of visualization to select.
        """
        self._available_visualization_type_region.get_by_role(
            "button", name=visualization_type
        ).click()

    def select_dropdown_option[T: DropdownOptions](
        self,
        dropdown_name: str,
        dropdown: Locator,
        option: T,
        text_input: Locator | None = None,
    ) -> None:
        """Select a dropdown option from a combobox of the wizard.

        Args:
            dropdown_name: the name of the dropdown for debugging.
            dropdown: the locator of the dropdown.
            option: the option to select.
            text_input: the text input locator if search to filter options will be made.
        """
        dropdown_helper = DropdownHelper[T](
            dropdown_name=dropdown_name,
            dropdown_box=dropdown,
            dropdown_list=self.locator().get_by_role("listbox"),
            text_input_filter=text_input,
        )
        dropdown_helper.select_option(option, search=(text_input is not None))

    def select_service_metric(
        self, metric_name: ServiceMetricDropdownOptions, search: bool = True
    ) -> None:
        """Select the service metric to use in the widget.

        Args:
            metric_name: name of the metric to choose.
            search: whether search to filter options will be made or not.
        """
        self.select_dropdown_option(
            "Service metric",
            self._service_metric_combobox,
            metric_name,
            self._combobox_text_input if search else None,
        )
