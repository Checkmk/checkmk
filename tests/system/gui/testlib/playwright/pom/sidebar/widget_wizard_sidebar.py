#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re
from enum import StrEnum
from typing import override

from playwright.sync_api import expect, Locator, Page

from tests.system.gui.testlib.playwright.dropdown import DropdownHelper, DropdownOptions
from tests.system.gui.testlib.playwright.pom.graphing.custom_graph_designer import (
    EmbeddedCustomGraphDesigner,
)
from tests.system.gui.testlib.playwright.pom.sidebar.base_sidebar import SidebarHelper
from tests.system.gui.testlib.playwright.pom.sidebar.widget_graph_legend_settings import (
    WidgetGraphLegendSettings,
)
from tests.system.gui.testlib.playwright.pom.sidebar.widget_time_range_settings import (
    WidgetTimeRangeSettings,
)

# A selection region restricted to one host or service offers that one field instead of the
# 'Add filter' menu, and the field carries no accessible name of its own.
_SINGLE_FILTER_SELECTOR = ".db-restricted-to-single-filter__container"

_SUGGESTIONS_SELECTOR = "ul.cmk-suggestions"
_SUGGESTIONS_FILTER_BOX_SELECTOR = "input[aria-label='filter']"

_WORKFLOW_LIST_SELECTOR = ".db-add-widget-dialog__container"


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

    @property
    def workflow_buttons(self) -> Locator:
        """Locator property of the buttons the sidebar currently offers, one per workflow."""
        return self.locator().locator(_WORKFLOW_LIST_SELECTOR).get_by_role("button")

    def _get_button_to_add_widget_by_type(self, wizard_class: type[BaseWidgetWizard]) -> Locator:
        """Get the button to add a new widget.

        Args:
            wizard_class: the wizard configuring the widget type of the button.

        Returns:
            The locator of the button to add the given widget type.
        """
        return self.locator().get_by_role("button", name=wizard_class.widget_type_name)

    def open_workflow_group(self, group_name: str) -> None:
        """Open a group of workflows, which lists its workflows in place of the widget types.

        Args:
            group_name: the name the sidebar gives the group.
        """
        self.locator().get_by_role("button", name=group_name).click()
        expect(
            self.locator().get_by_role("heading", name=group_name, exact=True),
            message=f"The sidebar did not open the '{group_name}' group",
        ).to_be_visible()

    def open_widget_wizard[W: BaseWidgetWizard](self, wizard_class: type[W]) -> W:
        """Open the wizard to add a new widget.

        Args:
            wizard_class: the wizard configuring the type of the widget that will be added.

        Returns:
            The wizard object of the open sidebar.
        """
        if wizard_class.widget_group_name is not None:
            self.open_workflow_group(wizard_class.widget_group_name)
        return self.select_widget_wizard(wizard_class)

    def select_widget_wizard[W: BaseWidgetWizard](self, wizard_class: type[W]) -> W:
        """Open a wizard the sidebar currently lists, so with its group already open.

        Args:
            wizard_class: the wizard configuring the type of the widget that will be added.

        Returns:
            The wizard object of the open sidebar.
        """
        self._get_button_to_add_widget_by_type(wizard_class).click()
        wizard = wizard_class(WizardDialogName.ADD_WIDGET, self.page)
        wizard.expect_to_be_visible()
        return wizard


class ServiceMetricDropdownOptions(DropdownOptions):
    CPU_UTILIZATION = "CPU utilization"
    TOTAL_EXECUTION_TIME = "Total execution time"


class SiteFilterDropdownOptions(DropdownOptions):
    LOCAL_SITE_GUI_E2E_CENTRAL = "Local site gui_e2e_central"


class VisualizationType(StrEnum):
    """Enumeration to define the type of visualization that a widget could have."""

    GRAPH = "Graph"
    METRIC = "Metric"
    GAUGE = "Gauge"
    BARPLOT = "Barplot"
    SCATTERPLOT = "Scatterplot"
    TOP_LIST = "Top list"


class AlertsVisualizationType(StrEnum):
    """Enumeration of the visualizations the 'Alerts & notifications' widget offers."""

    PERCENTAGE_OF_SERVICE_PROBLEMS = "Percentage of service problems"


class WizardDialogName(StrEnum):
    ADD_WIDGET = "Add widget to dashboard"
    EDIT_WIDGET = "Edit widget properties"


class BaseWidgetWizard(SidebarHelper):
    """Base class for widget wizard sidebar helpers."""

    # The name the UI gives the widget type when offering it, which is not necessarily the
    # heading the wizard itself carries.
    widget_type_name: str
    # The group offering the widget type, if it is not offered at the top level.
    widget_group_name: str | None = None

    def __init__(
        self, wizard_dialog_name: WizardDialogName, page: Page, validate_sidebar: bool = True
    ) -> None:
        self._wizard_dialog_name = wizard_dialog_name
        super().__init__(page, validate_sidebar)

    @property
    @override
    def _sidebar_locator(self) -> Locator:
        """Locator property for the main area of the sidebar."""
        return self._iframe_locator.get_by_role("dialog", name=self._wizard_dialog_name)

    @property
    def add_and_place_widget_button(self) -> Locator:
        """Locator property of 'Add & place widget' button."""
        return self.locator().get_by_role("button", name="Add & place widget")

    def _pick_suggestion(self, field: Locator, object_type: str, value: str) -> None:
        """Open the suggestions of `field` and pick `value` out of them."""
        field.click()

        suggestions = self.locator().locator(_SUGGESTIONS_SELECTOR)
        expect(suggestions, message=f"No list opened to offer {value!r}").to_be_visible()
        # Unqueried, the field offers every object there is and the backend caps how many
        # it returns, so narrow the list before picking out of it.
        filter_box = suggestions.locator(_SUGGESTIONS_FILTER_BOX_SELECTOR)
        expect(
            filter_box, message=f"The field offering {value!r} never showed its filter box"
        ).to_be_visible()
        filter_box.fill(value)
        option = suggestions.get_by_role("option", name=value, exact=True)
        expect(option, message=f"No {object_type} named {value!r} was offered").to_be_visible()
        option.click()
        # A field that did not take the value leaves the widget without its data, which
        # reads as missing data rather than a missing selection.
        expect(
            field, message=f"The field still does not show {value!r} after it was picked"
        ).to_contain_text(value)


class MetricsAndGraphsWidgetWizard(BaseWidgetWizard):
    """Represents the widget wizard sidebar to configure 'Metrics & graphs' widget

    To navigate: '{within any customized dashboard} > Add widget > Metrics & graphs'.
    """

    widget_type_name = "Metrics & graphs"
    sidebar_title = "Metrics & graphs"

    @property
    def _host_selection_region(self) -> Locator:
        """Locator property of 'Host selection' region."""
        return self.locator().get_by_role("region", name="Host selection")

    @property
    def _service_selection_region(self) -> Locator:
        """Locator property of 'Service selection' region."""
        return self.locator().get_by_role("region", name="Service selection")

    @property
    def _metric_selection_region(self) -> Locator:
        """Locator property of 'Host selection' region."""
        return self.locator().get_by_role("region", name="Metric selection")

    @property
    def _available_visualization_type_region(self) -> Locator:
        """Locator property of 'Available visualization type' region."""
        return self.locator().get_by_role("region", name="Available visualization type")

    @property
    def _combobox_text_input(self) -> Locator:
        """Locator property of the text input to search a value in a combobox."""
        return self.locator().locator("ul.cmk-suggestions").get_by_role("textbox")

    @property
    def single_metric_toggle(self) -> Locator:
        """Locator property of the toggle to select a single metric in 'Metric selection'."""
        return self._metric_selection_region.get_by_role("button", name="Toggle Metric (single)")

    @property
    def combined_graph_toggle(self) -> Locator:
        """Locator property of the toggle to select a combined graph in 'Metric selection'."""
        return self._metric_selection_region.get_by_role("button", name="Toggle Graph (combined)")

    @property
    def metric_selection_comboboxes(self) -> Locator:
        """Locator property of every combobox offered in the 'Metric selection' region."""
        return self._metric_selection_region.get_by_role("combobox")

    @property
    def service_metric_combobox(self) -> Locator:
        """Locator property of combobox to select the service metric of the widget."""
        return self._metric_selection_region.get_by_role("combobox", name="Select service metric")

    @property
    def service_graph_combobox(self) -> Locator:
        """Locator property of combobox to select the service graph of the widget."""
        # The field carries no accessible name; it is the only one the region offers while a
        # combined graph is selected.
        return self.metric_selection_comboboxes

    @property
    def next_step_visualization_button(self) -> Locator:
        """Locator property of 'Next step: Visualization' button."""
        return self.locator().get_by_role("button", name="Next step: Visualization")

    @property
    def save_widget_button(self) -> Locator:
        """Locator property of 'Save widget' button."""
        return self.locator().get_by_role("button", name="Save widget")

    @property
    def preview_title(self) -> Locator:
        """The title the visualization stage's preview gives the widget, as the dashboard will."""
        return self.locator().locator(".db-content-container__title")

    @property
    def time_range_settings(self) -> WidgetTimeRangeSettings:
        """The 'Time range' field of the visualization stage."""
        return WidgetTimeRangeSettings(self.locator())

    @property
    def graph_legend_settings(self) -> WidgetGraphLegendSettings:
        """The 'Legend' row of the visualization stage's 'Additional graph options'."""
        return WidgetGraphLegendSettings(self.locator())

    def expand_collapsed_panels(self) -> None:
        """Open every settings panel of the stage that starts out collapsed, such as
        'Additional graph options', so all the options it offers are rendered."""
        headers = self.locator().locator("button.cmk-catalog-panel__header")
        collapsed = headers.and_(self.locator().locator("[aria-expanded='false']"))
        # Bounded and confirmed per click: a header re-read before Vue re-rendered would be
        # clicked again and collapse back.
        for _ in range(collapsed.count()):
            header = collapsed.first
            panel_id = header.get_attribute("aria-controls")
            header.click()
            expect(
                headers.and_(self.locator().locator(f"[aria-controls='{panel_id}']")),
                message=f"The settings panel '{panel_id}' did not open",
            ).to_have_attribute("aria-expanded", "true")
        expect(collapsed, message="A settings panel of the stage is still collapsed").to_have_count(
            0
        )

    @property
    def _add_filter_section(self) -> Locator:
        """Locator property of 'Add filter' section."""
        return self._sidebar_locator.get_by_role("region", name="Add filter")

    def _get_filter_menu_item(self, item_name: str, exact: bool) -> Locator:
        """Get an item from filter menu.

        Args:
            item_name: the name of the item to get.
            exact: whether the name match has to be exact or not.

        Returns:
            The locator of the filter menu item.
        """
        return self._add_filter_section.get_by_role("button", name=item_name, exact=exact)

    def get_host_filter_container(self, filter_name: str) -> Locator:
        """Get the locator of the container of a filter from 'Host selection' region.

        Args:
            filter_name: the name of the filter of the container.

        Returns:
            The locator of the filter container.
        """
        return self._host_selection_region.get_by_role("group", name=filter_name)

    def get_host_filter_combobox(self, filter_name: str) -> Locator:
        """Get the locator of the combobox to set a host filter for the widget.

        Args:
            filter_name: the name of the filter that is set by the combobox.

        Returns:
            The locator of the combobox.
        """
        return self.get_host_filter_container(filter_name).get_by_role("combobox")

    def get_service_filter_container(self, filter_name: str) -> Locator:
        """Get the locator of the containe of a filter from 'Service selection' region.

        Args:
            filter_name: the name of the filter of the container.

        Returns:
            The locator of the filter container.
        """
        return self._service_selection_region.get_by_role("group", name=filter_name)

    def get_service_filter_combobox(self, filter_name: str) -> Locator:
        """Get the locator of the combobox to set a service filter for the widget.

        Args:
            filter_name: the name of the filter that is set by the combobox.

        Returns:
            The locator of the combobox.
        """
        return self.get_service_filter_container(filter_name).get_by_role("combobox")

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
            dropdown_list=self.locator().locator("ul.cmk-suggestions"),
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
            self.service_metric_combobox,
            metric_name,
            self._combobox_text_input if search else None,
        )

    def open_service_metric_dropdown(self) -> Locator:
        """Open the dropdown to select the service metric of the widget.

        Returns:
            The locator of the options the dropdown offers.
        """
        return self._open_dropdown("service metric", self.service_metric_combobox)

    def open_service_graph_dropdown(self) -> Locator:
        """Open the dropdown to select the service graph of the widget.

        Returns:
            The locator of the options the dropdown offers.
        """
        return self._open_dropdown("service graph", self.service_graph_combobox)

    def _open_dropdown(self, dropdown_name: str, combobox: Locator) -> Locator:
        """Open a dropdown of the wizard and return the locator of the options it offers."""
        combobox.click()
        suggestions = self.locator().locator(_SUGGESTIONS_SELECTOR)
        expect(suggestions, message=f"The {dropdown_name} dropdown did not open").to_be_visible()
        return suggestions.get_by_role("option")

    def select_single_host(self, host_name: str) -> None:
        """Restrict the widget to one host, in a region offering a single host.

        Args:
            host_name: the host to restrict the widget to.
        """
        self._select_single_object(self._host_selection_region, "host", host_name)

    def select_single_service(self, service_name: str) -> None:
        """Restrict the widget to one service, in a region offering a single service.

        Args:
            service_name: the service to restrict the widget to.
        """
        self._select_single_object(self._service_selection_region, "service", service_name)

    def _select_single_object(self, region: Locator, object_type: str, value: str) -> None:
        """Reveal the one field a restricted region offers and pick `value` in it."""
        # Not an exact match: the button's icon is an <img> without alt text, which some
        # engines still fold into the accessible name.
        region.get_by_role("button", name=f"Add {object_type} name").click()
        field = region.locator(_SINGLE_FILTER_SELECTOR).get_by_role("combobox")
        expect(field, message=f"No field to name a single {object_type} appeared").to_be_visible()
        self._pick_suggestion(field, object_type, value)

    def select_multiple_hosts_by_regex(self, host_regex: str) -> None:
        """Select every host matching a regular expression, in a region offering multiple hosts.

        Args:
            host_regex: the regular expression the names of the hosts have to match.
        """
        self._select_multiple_objects_by_regex(self._host_selection_region, "host", host_regex)

    def select_multiple_services_by_regex(self, service_regex: str) -> None:
        """Select every service matching a regular expression, in a region offering multiple
        services.

        Args:
            service_regex: the regular expression the names of the services have to match.
        """
        self._select_multiple_objects_by_regex(
            self._service_selection_region, "service", service_regex
        )

    def _select_multiple_objects_by_regex(
        self, region: Locator, object_type: str, regex: str
    ) -> None:
        """Switch a region to multiple objects and filter them by `regex` on their name."""
        region.get_by_role("button", name=f"Toggle Multiple {object_type}s").click()
        filter_name = f"{object_type.capitalize()} name (regex)"
        self._add_filter(region, filter_name, sub_menu=f"{object_type.capitalize()} name")
        field = region.get_by_role("group", name=filter_name).get_by_role("combobox")
        expect(field, message=f"No field to filter {object_type}s by name appeared").to_be_visible()
        self._pick_suggestion(field, object_type, regex)

    def add_filter_to_host_selection(self, filter_name: str, sub_menu: str | None = None) -> None:
        """Add filter to widget in host selection region.

        Args:
            filter_name: name of the filter to add.
            exact: whether the name match has to be exact or not.
        """
        self._add_filter(self._host_selection_region, filter_name, sub_menu)

    def _add_filter(self, region: Locator, filter_name: str, sub_menu: str | None) -> None:
        """Add a filter to the widget in a selection region."""
        region.get_by_role("button", name="Add filter").click()
        expect(
            self._add_filter_section, message="'Add filter' section is not visible"
        ).to_be_visible()

        filter_menu_item = self._get_filter_menu_item(filter_name, exact=True)

        if sub_menu is not None and not filter_menu_item.is_visible():
            self._add_filter_section.get_by_role("button", name=sub_menu).click()
            expect(
                filter_menu_item,
                message=f"Filter menu item '{filter_name}' not visible",
            ).to_be_visible()

        filter_menu_item.click()

    def remove_filter_from_host_selection(self, filter_name: str) -> None:
        """Remove filter from host selection region.

        Args:
            filter_name: name of the filter to remove.
        """
        self._host_selection_region.get_by_role(
            "button", name=f"Remove {filter_name} filter"
        ).click()


class AlertsAndNotificationsWidgetWizard(BaseWidgetWizard):
    """Represents the widget wizard sidebar to configure an 'Alerts & notifications' widget.

    To navigate: '{within any customized dashboard} > Add widget > Alerts & notifications'.
    """

    widget_type_name = "Alerts & notifications"
    # The heading names the widget in the singular, unlike the tile that opens the wizard.
    sidebar_title = "Alert & Notification"

    @property
    def _available_visualization_types_region(self) -> Locator:
        """Locator property of 'Available visualization types' region."""
        return self.locator().get_by_role("region", name="Available visualization types")

    def select_visualization_type(self, visualization_type: AlertsVisualizationType) -> None:
        """Select the type of visualization for the widget.

        Args:
            visualization_type: type of visualization to select.
        """
        self._available_visualization_types_region.get_by_role(
            "button", name=visualization_type
        ).click()


class _CustomGraphWidgetWizard(BaseWidgetWizard):
    """Base class for the wizards of the 'Custom graphs' group, which share their heading."""

    widget_group_name: str | None = "Custom graphs"
    sidebar_title = "Custom graphs"

    def set_widget_title(self, title: str) -> None:
        """Replace the widget's default title, which only names the graph once it is drawn.

        Args:
            title: the title the widget shows.
        """
        panel = (
            self.locator()
            .locator(".cmk-catalog-panel")
            .filter(has=self.page.locator(".cmk-catalog-panel__header", has_text="Widget settings"))
        )
        row = panel.locator(".table-form-row").filter(
            has=self.page.get_by_text("Title", exact=True)
        )
        row.get_by_role("textbox").fill(title)


class LinkCustomGraphWidgetWizard(_CustomGraphWidgetWizard):
    """Represents the widget wizard sidebar linking a custom graph of the graph catalog.

    The widget refers to the catalog graph, so it follows later edits of that graph.

    To navigate: '{within any customized dashboard} > Add widget > Custom graphs >
    Link existing custom graph'.
    """

    widget_type_name = "Link existing custom graph"

    @property
    def custom_graph_combobox(self) -> Locator:
        """Locator property of the dropdown to select the linked graph; shows its title."""
        # The dropdown carries no accessible name of its own, only the row it sits in does.
        row = (
            self.locator()
            .locator(".table-form-row")
            .filter(has=self.page.get_by_text("Custom graph", exact=True))
        )
        return row.get_by_role("combobox")

    def select_custom_graph(self, graph_title: str) -> None:
        """Link the catalog graph titled `graph_title`.

        Args:
            graph_title: the title of the custom graph to link.
        """
        self._pick_suggestion(self.custom_graph_combobox, "custom graph", graph_title)


class _EmbeddedCustomGraphWidgetWizard(_CustomGraphWidgetWizard):
    """Base class for the wizards keeping the graph definition in the widget itself.

    Stage 1 edits the definition in an embedded designer, stage 2 the widget settings, from
    where the definition can also be saved to the graph catalog.
    """

    @property
    def designer(self) -> EmbeddedCustomGraphDesigner:
        """The designer of stage 1, editing the definition the widget will keep."""
        return EmbeddedCustomGraphDesigner(self.page, self.locator())

    @property
    def save_to_graph_catalog_button(self) -> Locator:
        """Locator property of the stage 2 button to save the definition to the graph catalog.

        Offered only to users who may edit custom graphs.
        """
        return self.locator().get_by_role("button", name="Save to graph catalog", exact=True)

    def go_to_widget_settings(self) -> None:
        """Move on from the designer to the widget settings (stage 2)."""
        self.locator().get_by_role("button", name="Next step: Widget settings").click()
        expect(
            self.locator().get_by_role("heading", name="Widget data", exact=True),
            message="The wizard did not move on to the widget settings",
        ).to_be_visible()

    def save_to_graph_catalog(self, graph_title: str, graph_name: str) -> None:
        """Save the definition as a new catalog graph, which the widget then links.

        Also adds or saves the widget, so the wizard closes.

        Args:
            graph_title: the title of the new catalog graph.
            graph_name: the unique ID of the new catalog graph.
        """
        self.save_to_graph_catalog_button.click()
        # A popup, so it is portalled out of the wizard.
        popup = self._iframe_locator.get_by_role("dialog", name="Save to custom graph catalog")
        expect(popup, message="The popup to save to the graph catalog did not open").to_be_visible()
        popup.get_by_label("Title").fill(graph_title)
        popup.get_by_label("Unique ID").fill(graph_name)
        # The button names the widget action: "& place widget" when adding, "& save" editing.
        popup.get_by_role("button", name=re.compile(r"^Save to catalog & ")).click()
        expect(
            popup, message="The popup to save to the graph catalog did not close"
        ).not_to_be_visible()


class NewCustomGraphWidgetWizard(_EmbeddedCustomGraphWidgetWizard):
    """Represents the widget wizard sidebar building a new graph definition for the widget.

    To navigate: '{within any customized dashboard} > Add widget > Custom graphs >
    New custom graph'.
    """

    widget_type_name = "New custom graph"


class CloneCustomGraphWidgetWizard(_EmbeddedCustomGraphWidgetWizard):
    """Represents the widget wizard sidebar copying a catalog graph's definition into the widget.

    Edits change the widget's copy only, never the catalog graph.

    To navigate: '{within any customized dashboard} > Add widget > Custom graphs >
    Clone custom graph'.
    """

    widget_type_name = "Clone custom graph"

    def clone_custom_graph(self, graph_title: str) -> None:
        """Copy the catalog graph titled `graph_title` into the designer.

        Args:
            graph_title: the title of the custom graph to clone.
        """
        # Named so before and after a graph was picked, by its text and its label in turn.
        self.locator().get_by_role("button", name="Clone custom graph").click()
        # A menu, so it is portalled out of the wizard.
        menu = self._iframe_locator.get_by_role("menu")
        expect(menu, message="The menu of graphs to clone did not open").to_be_visible()
        menu.get_by_placeholder("Search custom graphs ...").fill(graph_title)
        menu.get_by_role("menuitem", name=graph_title, exact=True).click()
        expect(
            self.locator().get_by_role("heading", name=graph_title, exact=True),
            message=f"The wizard does not name {graph_title!r} as the graph it cloned",
        ).to_be_visible()
        self.designer.expect_loaded()
