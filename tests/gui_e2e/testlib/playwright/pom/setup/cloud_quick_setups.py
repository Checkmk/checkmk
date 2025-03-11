#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import Literal, NamedTuple, override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class QuickSetupMultiChoice(NamedTuple):
    """Consolidate name of items, the state of which can be toggled.

    Examples of such items available on the UI include checkboxes.
    """

    to_activate: list[str]
    to_deactivate: list[str]


class AWSAddNewConfiguration(CmkPage):
    """Represent the page 'Add Amazon Web Services (AWS) configuration' to add an AWS configuration.

    Accessible at,
    Setup > Quick Setup > Amazon Web Services (AWS) > Add Amazon Web Services (AWS) configuration
    """

    suffix = "aws"
    page_title = "Add Amazon Web Services (AWS) configuration"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to 'AWS Quick setup > Add Amazon Web Services configuration' page")
        quick_setup_aws = AWSConfigurationList(self.page)
        quick_setup_aws.add_configuration_button.click()
        _url_pattern: str = quote_plus(
            "wato.py?mode=new_special_agent_configuration&varname=special_agents"
        )
        self.page.wait_for_url(
            url=re.compile(_url_pattern + f".+{self.suffix}$"),
            wait_until="load",
        )
        self._validate_page()

    @override
    def _validate_page(self) -> None:
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def button_proceed_from_stage_one(self) -> Locator:
        return self._button_proceed_from_stage("Configure host and regions")

    @property
    def button_proceed_from_stage_two(self) -> Locator:
        return self._button_proceed_from_stage("Configure services to monitor")

    @property
    def button_proceed_from_stage_three(self) -> Locator:
        return self._button_proceed_from_stage("Review and test configuration")

    @property
    def button_proceed_from_stage_four(self) -> Locator:
        return self._button_proceed_from_stage("Test configuration")

    @property
    def save_and_go_to_activate_changes_button(self) -> Locator:
        return self.main_area.locator().get_by_role("button", name="Save")

    def _get_row(self, name: str) -> Locator:
        # TODO: change to accessibility elements once available
        return self.main_area.locator(
            f'div[class*="form-dictionary"]:has(span > span:has-text("{name}"))'
        )

    # stage-2
    def regions_to_monitor_table(
        self, type_: Literal["available", "active"] | None = None
    ) -> Locator:
        table_ = self._get_row("Regions to monitor")
        if type_:
            return table_.get_by_role("listbox", name=type_)
        return table_

    # ----

    # stage-3
    def check_service_per_region(self, service: str, check: bool) -> None:
        service_checkbox = self._checkbox_service_in_row("Services per region", service)
        if service_checkbox.is_checked() != check:
            service_checkbox.click()

    def check_global_service(self, service: str, check: bool) -> None:
        service_checkbox = self._checkbox_service_in_row("Global services", service)
        if service_checkbox.is_checked() != check:
            service_checkbox.click()

    def _checkbox_service_in_row(self, row_name: str, name: str) -> Locator:
        return self._get_row(row_name).get_by_text(name)

    # ----

    def _button_proceed_from_stage(self, button_text: str) -> Locator:
        # TODO: change to access via .get_by_role("button", name="<buttonId>")
        #  after an id has been added
        return (
            self.main_area.locator()
            .get_by_label("Go to the next stage")
            .get_by_text(button_text, exact=True)
        )

    def initialize_table(self, table: Locator, data: QuickSetupMultiChoice) -> None:
        for element in data.to_activate:
            table.get_by_role("option", name=element).click()
            table.get_by_role("button", name=">").click()

        for element in data.to_deactivate:
            table.get_by_role("option", name=element).click()
            table.get_by_role("button", name="<").click()

    def specify_stage_one_details(
        self, configuration_name: str, access_key: str, access_password: str
    ) -> None:
        logger.info("Initialize stage-1 details.")
        self._get_row("Configuration name").get_by_role("textbox").fill(configuration_name)
        self._get_row("Access key ID").get_by_role("textbox").fill(access_key)
        self._get_row("Secret access key").get_by_role("combobox").click()
        self._get_row("Secret access key").get_by_role("option", name="Explicit").click()
        self._get_row("Secret access key").locator('input[type="password"]').fill(access_password)

    def specify_stage_two_details(
        self, host_name: str, host_path: str, regions_to_monitor: list[str], site_name: str
    ) -> None:
        # TODO: change to accessibility elements once available
        logger.info("Initialize stage-2 details.")
        self._get_row("Host name").get_by_role("textbox").fill(host_name)
        self._get_row("Folder").get_by_role("textbox").fill(host_path)
        for region in regions_to_monitor:
            self.regions_to_monitor_table("available").get_by_role("option", name=region).click()
            self.regions_to_monitor_table().get_by_role("button", name="Add >").click()

        self._get_row("Site selection").get_by_role("combobox").click()
        self._get_row("Site selection").get_by_role(
            "option", name=f"{site_name} - Local site {site_name}"
        )

    def specify_stage_three_details(
        self, services_per_region: QuickSetupMultiChoice, global_services: QuickSetupMultiChoice
    ) -> None:
        logger.info("Initialize stage-3 details.")
        for entry in services_per_region.to_activate:
            self.check_service_per_region(entry, True)
        for entry in services_per_region.to_deactivate:
            self.check_service_per_region(entry, False)

        for entry in global_services.to_activate:
            self.check_global_service(entry, True)
        for entry in global_services.to_activate:
            self.check_global_service(entry, False)

    def save_quick_setup(self) -> None:
        logger.info("Save AWS configuration.")
        self.save_and_go_to_activate_changes_button.click()
        self.activate_selected()
        self.expect_success_state()


class AWSConfigurationList(CmkPage):
    """Represent the page 'Amazon Web Services (AWS)', which lists the configuration setup.

    Accessible at,
    Setup > Quick Setup > Amazon Web Services (AWS)
    """

    suffix = "aws"
    page_title = "Amazon Web Services (AWS)"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        self.main_menu.setup_menu("Amazon Web Service (AWS)").click()
        _url_pattern: str = quote_plus(
            "wato.py?mode=edit_configuration_bundles&varname=special_agents"
        )
        self.page.wait_for_url(
            url=re.compile(f"{_url_pattern}.+{self.suffix}$"),
            wait_until="load",
        )
        self._validate_page()

    @override
    def _validate_page(self) -> None:
        self.main_area.check_page_title(self.page_title)
        expect(self.add_configuration_button).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def add_configuration_button(self) -> Locator:
        return (
            self.main_area.locator()
            .get_by_role("cell", name="Add configuration")
            .get_by_role("link")
        )

    def configuration_row(self, name: str) -> Locator:
        return self.main_area.locator(f"tr[class*='data']:has(td:has-text('{name}'))")

    def delete_configuration(self, configuration_name: str) -> None:
        (
            self.configuration_row(configuration_name)
            .get_by_role("link", name="Delete this configuration")
            .click()
        )
        self.main_area.locator().get_by_role("button", name="Delete").click()
        expect(self.configuration_row(configuration_name)).not_to_be_visible()
