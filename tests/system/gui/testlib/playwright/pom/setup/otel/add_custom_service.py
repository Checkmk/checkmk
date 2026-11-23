#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import override

from playwright.sync_api import expect, Locator, Page

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.graphing.graph_accessor import (
    ENGINE_GRAPH_PANEL_SELECTOR,
)
from tests.system.gui.testlib.playwright.pom.graphing.timeseries_graph import GraphPanel
from tests.system.gui.testlib.playwright.pom.page import CmkPage
from tests.system.gui.testlib.playwright.pom.setup.otel.custom_services import CustomServices
from tests.system.gui.testlib.playwright.pom.setup.otel.suggestions import Suggestions
from tests.system.gui.testlib.playwright.pom.setup.otel.telemetry_metrics_query_form import (
    TelemetryMetricsQueryForm,
)

logger = logging.getLogger(__name__)


class CustomServiceWizard(CmkPage):
    """The wizard of a custom service: name the configuration, define the metric, assign a host.

    Editing a service opens it at the metric step; the configuration name stays as it is.
    """

    page_title: str

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    # Every step

    @property
    def active_step(self) -> Locator:
        """The wizard step currently open.

        The other steps stay in the page, collapsed, with buttons of the same name. The
        wizard marks the open step for assistive technology with `aria-current="step"`.
        """
        return self.main_area.locator("[aria-current='step']")

    def step_heading(self, title: str) -> Locator:
        return self.active_step.get_by_role("heading", name=title, exact=True)

    @property
    def next_step_button(self) -> Locator:
        return self.active_step.get_by_role("button", name="Next step", exact=True)

    def go_to_next_step(self, heading: str) -> None:
        """Click 'Next step' and wait until the step titled `heading` is open."""
        logger.info("Go to the step '%s'", heading)
        self.next_step_button.click()
        expect(
            self.step_heading(heading), f"The wizard did not move on to the step {heading!r}"
        ).to_be_visible()

    # Step 2: Define metric

    @property
    def metric_query(self) -> TelemetryMetricsQueryForm:
        return TelemetryMetricsQueryForm(self.active_step, self.main_area)

    @property
    def graph_preview(self) -> GraphPanel:
        """The preview graph, the same panel the other graph pages render."""
        return GraphPanel(
            self.active_step.locator(ENGINE_GRAPH_PANEL_SELECTOR), self.page, self.main_area
        )

    # Step 3: Assign to host

    @property
    def service_name_input(self) -> Locator:
        return self.active_step.get_by_role("textbox", name="Service name")

    @property
    def host_select(self) -> Locator:
        return self.active_step.get_by_role("combobox", name=re.compile(r"^Select host\b"))

    def assign_host(self, host_name: str) -> None:
        """Search for `host_name` in the host dropdown and pick it."""
        logger.info("Select host '%s'", host_name)
        self.host_select.click()
        self._suggestions.search(host_name)
        self._suggestions.pick(host_name)
        expect(self.host_select, f"Host {host_name!r} was not selected").to_contain_text(host_name)

    def assignment_tab(self, title: str) -> Locator:
        """The tab choosing how the service is assigned: "Manual" or "Automatic"."""
        return self.active_step.get_by_role("tab", name=title, exact=True)

    @property
    def host_name_template_input(self) -> Locator:
        return self.active_step.get_by_role("textbox", name="Host name template")

    def template_attribute_button(self, attribute_key: str) -> Locator:
        """The button appending the placeholder of `attribute_key` to the host name template."""
        return self.active_step.get_by_role("button", name=f"+ {attribute_key}", exact=True)

    def type_into_host_name_template(self, text: str) -> None:
        """Type `text` at the end of the host name template, keeping what is already there."""
        self.host_name_template_input.focus()
        self.host_name_template_input.press("End")
        self.host_name_template_input.press_sequentially(text)

    @property
    def no_host_name_warning(self) -> Locator:
        return self.active_step.get_by_text(
            "This template currently resolves to no host name, so the service cannot be saved."
        )

    @property
    def target_hosts(self) -> Locator:
        """The configured hosts the host name template matches, as a comma separated list."""
        return self._labelled_value("Target hosts:")

    @property
    def new_hosts(self) -> Locator:
        """The host names of no configured host, which saving creates.

        They go to the Main folder unless another folder is chosen for them.
        """
        return self._labelled_value("New hosts, created on saving:")

    def _labelled_value(self, label: str) -> Locator:
        return self.active_step.locator("span", has_text=label).locator("strong")

    # Dropdowns of every step

    @property
    def _suggestions(self) -> Suggestions:
        return Suggestions(self.main_area)


class AddCustomService(CustomServiceWizard):
    """Represent the page `Setup -> Telemetry -> Custom Services -> Add custom service`."""

    page_title = "Add custom service"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        custom_services_page = CustomServices(self.page)
        self.click_and_wait_for_navigation(
            custom_services_page.add_custom_service_button,
            frame_url=re.compile("mode=create_otel_custom_service"),
        )
        self.validate_page()

    @property
    def configuration_name_input(self) -> Locator:
        return self.active_step.get_by_role("textbox", name="Configuration name")

    @property
    def create_and_activate_button(self) -> Locator:
        return self.active_step.get_by_role("button", name="Create & activate changes", exact=True)


class EditCustomService(CustomServiceWizard):
    """Represent the page `Setup -> Telemetry -> Custom Services -> Edit custom service`."""

    page_title = "Edit custom service"

    def __init__(self, page: Page, service_name: str, navigate_to_page: bool = True) -> None:
        self.service_name = service_name
        super().__init__(page, navigate_to_page)

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page of '%s'", self.page_title, self.service_name)
        custom_services_page = CustomServices(self.page)
        self.click_and_wait_for_navigation(
            custom_services_page.edit_button(self.service_name),
            frame_url=re.compile("mode=edit_otel_custom_service"),
        )
        self.validate_page()

    @property
    def save_and_activate_button(self) -> Locator:
        return self.active_step.get_by_role("button", name="Save & activate changes", exact=True)
