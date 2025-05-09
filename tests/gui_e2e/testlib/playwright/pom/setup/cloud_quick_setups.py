#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from abc import abstractmethod
from typing import Final, Literal, NamedTuple, override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator, Page

from tests.gui_e2e.testlib.playwright.dropdown import DropdownHelper, DropdownOptions
from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.gui_e2e.testlib.playwright.timeouts import ANIMATION_TIMEOUT

logger = logging.getLogger(__name__)


class QuickSetupMultiChoice(NamedTuple):
    """Consolidate name of items, the state of which can be toggled.

    Examples of such items available on the UI include checkboxes.
    """

    to_activate: list[str]
    to_deactivate: list[str]


class BaseQuickSetupConfigurationList(CmkPage):
    """Base class for quick setup configuration list pages."""

    @property
    @abstractmethod
    def suffix(self) -> str:
        pass

    @property
    @abstractmethod
    def page_title(self) -> str:
        pass

    @property
    def setup_entry(self) -> str:
        return self.page_title

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        self.main_menu.setup_menu(self.setup_entry).click()
        _url_pattern: str = quote_plus(
            "wato.py?mode=edit_configuration_bundles&varname=special_agents"
        )
        self.page.wait_for_url(
            url=re.compile(f"{_url_pattern}.+{self.suffix}$"),
            wait_until="load",
        )
        self.validate_page()

    @override
    def validate_page(self) -> None:
        self.main_area.check_page_title(self.page_title)
        expect(
            self.add_configuration_button,
            message="Expected 'Add configuration' button to be visible!",
        ).to_be_visible()

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
        expect(
            self.configuration_row(configuration_name),
            message=f"Expected the configuration '{configuration_name}' to be deleted!",
        ).not_to_be_visible()


class PasswordType(DropdownOptions):
    """Represent the options of the password type dropdown."""

    EXPLICIT = "Explicit"
    FROM_PASSWORD_STORE = "From password store"


class BaseQuickSetupAddNewConfiguration(CmkPage):
    """Base class for adding quick setup configuration pages."""

    class FolderDetails:
        def __init__(self, parent: str, name: str, create_new: bool) -> None:
            self.parent: Final[str] = parent
            self.name: Final[str] = name
            self.create_new: Final[bool] = create_new

    @property
    @abstractmethod
    def suffix(self) -> str:
        pass

    @property
    @abstractmethod
    def page_title(self) -> str:
        pass

    @abstractmethod
    def list_configuration_page(self) -> BaseQuickSetupConfigurationList:
        pass

    def __init__(
        self,
        page: Page,
        configuration_name: str,
        folder_details: FolderDetails,
        navigate_to_page: bool = True,
        contain_filter_sidebar: bool = False,
        timeout_assertions: int | None = None,
        timeout_navigation: int | None = None,
    ) -> None:
        super().__init__(
            page=page,
            navigate_to_page=navigate_to_page,
            contain_filter_sidebar=contain_filter_sidebar,
            timeout_assertions=timeout_assertions,
            timeout_navigation=timeout_navigation,
        )
        self.configuration_name: Final[str] = configuration_name
        self.folder_details: Final[BaseQuickSetupAddNewConfiguration.FolderDetails] = folder_details

    @override
    def navigate(self) -> None:
        logger.info(f"Navigate to 'Quick setup > {self.page_title}' page")
        list_page = self.list_configuration_page()
        list_page.add_configuration_button.click()
        _url_pattern: str = quote_plus(
            "wato.py?mode=new_special_agent_configuration&varname=special_agents"
        )
        self.page.wait_for_url(
            url=re.compile(_url_pattern + f".+{self.suffix}$"),
            wait_until="load",
        )
        self.validate_page()

    @override
    def validate_page(self) -> None:
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def save_and_go_to_activate_changes_button(self) -> Locator:
        return self.main_area.locator().get_by_role("button", name="Save")

    @property
    def quick_setup_area(self) -> Locator:
        """Get main area of the quick setup."""
        return self.main_area.locator("ol.quick-setup")

    @property
    def password_type_dropdown(self) -> DropdownHelper[PasswordType]:
        """Represent the password type dropdown for the quick setup configuration pages."""
        return DropdownHelper[PasswordType](
            dropdown_name="Password type",
            dropdown_box=self.quick_setup_area.get_by_role("combobox", name="Choose password type"),
            dropdown_list=self.quick_setup_area.get_by_role("listbox"),
        )

    def save_quick_setup(self) -> None:
        logger.info("Save Quick setup configuration.")
        self.save_and_go_to_activate_changes_button.click()
        self.activate_selected()
        self.expect_success_state()

    def _get_row(self, name: str) -> Locator:
        # TODO: change to accessibility elements once available
        return self.main_area.locator(
            f'div[class*="form-dictionary"]:has(span > span:has-text("{name}"))'
        )

    def _button_proceed_from_stage(self, button_text: str) -> Locator:
        # TODO: change to access via .get_by_role("button", name="<buttonId>")
        #  after an id has been added
        return (
            self.main_area.locator()
            .get_by_label("Go to the next stage")
            .get_by_text(button_text, exact=True)
        )

    def _select_folder(self, folder_path: str) -> None:
        main_area = self.main_area.locator()
        main_area.get_by_role("combobox", name="Folder").click()
        main_area.get_by_role("option", name=folder_path, exact=True).click()

    def _create_folder(self, parent: str, name: str) -> None:
        main_area = self.main_area.locator()
        # `force=True` - prevents UI from sliding out of view during test runs
        create_new_button = main_area.get_by_role("button", name="Create new")
        expect(
            create_new_button,
            message="Expected 'button' to create new folders (within quick setup) to be visible!",
        ).to_be_visible()
        create_new_button.click(force=True)
        self.page.wait_for_timeout(ANIMATION_TIMEOUT)
        dialog = main_area.get_by_role("dialog", name="New folder")
        dialog.get_by_role("textbox", name="Title").fill(name)
        dialog.get_by_role("combobox", name="Parent folder").click()
        dialog.get_by_role("option", name=parent, exact=True).click()
        dialog.get_by_role("button", name="Save").click()
        self.page.wait_for_timeout(ANIMATION_TIMEOUT)

    def _handle_folder_selection(
        self,
        folder_name: str,
        parent_path: str | None = None,
        create_new: bool = False,
    ) -> None:
        """Select the folder, optionally creating it first.

        The folder_name is only the last folder in the whole path.
        The parent_path is all previous folders, separated by a slash.
        If create_new is True, the folder will be created. The parent must be specified and exist.
        """
        folder_path = f"{parent_path}/{folder_name}" if parent_path else folder_name
        # Main folder is not included in the paths for subfolders for some reason
        folder_path = folder_path.removeprefix("Main/")
        if create_new:
            assert isinstance(
                parent_path, str
            ), "Parent path must be provided to create a new folder."
            # Main folder is not included in the paths for subfolders for some reason
            # the parent_path must stay as "Main", if that is specified though
            parent_path = parent_path.removeprefix("Main/")
            self._create_folder(parent_path, folder_name)
            # the newly created folder is automatically selected
        else:
            self._select_folder(folder_path)

        expect(
            self.main_area.locator().get_by_role("combobox", name="Folder"),
            message=f"Expected '{folder_path}' to be selected in dropdown menu!",
        ).to_have_text(folder_path)

    def _checkbox_service_in_row(self, row_name: str, name: str) -> Locator:
        return self._get_row(row_name).get_by_text(name)

    def fill_explicit_password(self, password: str) -> None:
        """Fill the explicit password field with the given password.

        Args:
            password: The password to fill in.
        """
        self.password_type_dropdown.select_option(PasswordType.EXPLICIT)
        self.main_area.locator().get_by_role("textbox", name="explicit password").fill(password)


class AWSConfigurationList(BaseQuickSetupConfigurationList):
    """Represent the page 'Amazon Web Services (AWS)', which lists the configuration setup.

    Accessible at,
    Setup > Quick Setup > Amazon Web Services (AWS)
    """

    suffix = "aws"
    page_title = "Amazon Web Services (AWS)"
    setup_entry = "Amazon Web Service (AWS)"


class AWSAddNewConfiguration(BaseQuickSetupAddNewConfiguration):
    """Represent the page 'Add Amazon Web Services (AWS) configuration' to add an AWS configuration.

    Accessible at,
    Setup > Quick Setup > Amazon Web Services (AWS) > Add Amazon Web Services (AWS) configuration
    """

    suffix = "aws"
    page_title = "Add Amazon Web Services (AWS) configuration"

    @override
    def list_configuration_page(self) -> AWSConfigurationList:
        return AWSConfigurationList(self.page)

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

    # ----

    def specify_stage_one_details(self, access_key: str, access_password: str) -> None:
        logger.info("Initialize stage-1 details.")
        self._get_row("Configuration name").get_by_role("textbox").fill(self.configuration_name)
        self._get_row("Access key ID").get_by_role("textbox").fill(access_key)
        self.fill_explicit_password(access_password)

    def specify_stage_two_details(
        self, host_name: str, regions_to_monitor: list[str], site_name: str
    ) -> None:
        # TODO: change to accessibility elements once available
        logger.info("Initialize stage-2 details.")
        self._get_row("Host name").get_by_role("textbox").fill(host_name)
        self._handle_folder_selection(
            folder_name=self.folder_details.name,
            parent_path=self.folder_details.parent,
            create_new=self.folder_details.create_new,
        )
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


class GCPConfigurationList(BaseQuickSetupConfigurationList):
    """Represent the page 'Google Cloud Platform (GCP)', which lists the configuration setup.

    Accessible at,
    Setup > Quick Setup > Google Cloud Platform (GCP)
    """

    suffix = "gcp"
    page_title = "Google Cloud Platform (GCP)"


class GCPAddNewConfiguration(BaseQuickSetupAddNewConfiguration):
    """Represent the page 'Add Google Cloud Platform (GCP) configuration' to add a GCP
    configuration.

    Accessible at,
    Setup > Quick Setup > Google Cloud Platform (GCP)
        > Add Google Cloud Platform (GCP) configuration
    """

    suffix = "gcp"
    page_title = "Add Google Cloud Platform (GCP) configuration"

    @override
    def list_configuration_page(self) -> GCPConfigurationList:
        return GCPConfigurationList(self.page)

    @property
    def button_proceed_from_stage_one(self) -> Locator:
        return self._button_proceed_from_stage("Configure host")

    @property
    def button_proceed_from_stage_two(self) -> Locator:
        return self._button_proceed_from_stage("Configure services to monitor")

    @property
    def button_proceed_from_stage_three(self) -> Locator:
        return self._button_proceed_from_stage("Review and test configuration")

    @property
    def button_proceed_from_stage_four(self) -> Locator:
        return self._button_proceed_from_stage("Test configuration")

    # stage-3
    def check_service(self, service: str, check: bool) -> None:
        service_checkbox = self._get_row("GCP services to monitor").get_by_text(service)
        if service_checkbox.is_checked() != check:
            service_checkbox.click()

    # ----

    def specify_stage_one_details(self, project_id: str, json_credentials: str) -> None:
        logger.info("Initialize stage-1 details.")
        main_area = self.main_area.locator()
        main_area.get_by_role("textbox", name="Configuration name").fill(self.configuration_name)
        main_area.get_by_role("textbox", name="Project ID").fill(project_id)
        self.fill_explicit_password(json_credentials)

    def specify_stage_two_details(self, host_name: str, site_name: str) -> None:
        logger.info("Initialize stage-2 details.")
        main_area = self.main_area.locator()
        main_area.get_by_role("textbox", name="Host name").fill(host_name)
        self._handle_folder_selection(
            folder_name=self.folder_details.name,
            parent_path=self.folder_details.parent,
            create_new=self.folder_details.create_new,
        )
        main_area.get_by_role("combobox", name="Site selection").click()
        main_area.get_by_role("option", name=f"{site_name} - Local site").click()

    def specify_stage_three_details(self, services: QuickSetupMultiChoice) -> None:
        logger.info("Initialize stage-3 details.")
        for entry in services.to_activate:
            self.check_service(entry, True)
        for entry in services.to_deactivate:
            self.check_service(entry, False)


class AzureConfigurationList(BaseQuickSetupConfigurationList):
    """Represent the page 'Microsoft Azure', which lists the configuration setup.

    Accessible at,
    Setup > Quick Setup > Microsoft Azure
    """

    suffix = "azure"
    page_title = "Microsoft Azure"


class Authority(DropdownOptions):
    """Represent the options of the authority dropdown for Azure configuration."""

    GLOBAL = "Global"
    CHINA = "China"


class AzureAddNewConfiguration(BaseQuickSetupAddNewConfiguration):
    """Represent the page 'Add Microsoft Azure configuration' to add a GCP
    configuration.

    Accessible at,
    Setup > Quick Setup > Microsoft Azure
        > Add Microsoft Azure configuration
    """

    suffix = "azure"
    page_title = "Add Microsoft Azure configuration"

    @override
    def list_configuration_page(self) -> AzureConfigurationList:
        return AzureConfigurationList(self.page)

    @property
    def button_proceed_from_stage_one(self) -> Locator:
        return self._button_proceed_from_stage("Configure host and authority")

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
    def authority_dropdown(self) -> DropdownHelper[Authority]:
        """Represent the authority dropdown for Azure configuration."""
        return DropdownHelper[Authority](
            dropdown_name="Authority",
            dropdown_box=self.quick_setup_area.get_by_role("combobox", name="Authority"),
            dropdown_list=self.quick_setup_area.get_by_role("listbox"),
        )

    def check_service_to_monitor(self, service: str, check: bool) -> None:
        service_checkbox = self._checkbox_service_in_row("Azure services to monitor", service)
        if service_checkbox.is_checked() != check:
            service_checkbox.click()

    def specify_stage_one_details(
        self, subscription_id: str, tenant_id: str, client_id: str, secret: str
    ) -> None:
        logger.info("Initialize stage-1 details.")
        main_area = self.main_area.locator()
        main_area.get_by_role("textbox", name="Configuration name").fill(self.configuration_name)
        main_area.get_by_role("textbox", name="Subscription ID").fill(subscription_id)
        main_area.get_by_role("textbox", name="Tenant ID / Directory ID").fill(tenant_id)
        main_area.get_by_role("textbox", name="Client ID / Application ID").fill(client_id)

        self.fill_explicit_password(secret)

        self.authority_dropdown.select_option(Authority.GLOBAL)

    def specify_stage_two_details(self, host_name: str, site_name: str) -> None:
        logger.info("Initialize stage-2 details.")
        main_area = self.main_area.locator()
        main_area.get_by_role("textbox", name="Host name").fill(host_name)

        main_area.get_by_role("combobox", name="Site selection").click()
        main_area.get_by_role("option", name=f"{site_name} - Local site").click()

        self._handle_folder_selection(
            folder_name=self.folder_details.name,
            parent_path=self.folder_details.parent,
            create_new=self.folder_details.create_new,
        )

    def specify_stage_three_details(
        self,
        services_to_monitor: QuickSetupMultiChoice,
    ) -> None:
        logger.info("Initialize stage-3 details.")
        for entry in services_to_monitor.to_activate:
            self.check_service_to_monitor(entry, True)
        for entry in services_to_monitor.to_deactivate:
            self.check_service_to_monitor(entry, False)
