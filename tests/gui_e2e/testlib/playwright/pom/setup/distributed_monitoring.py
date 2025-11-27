#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from enum import StrEnum
from typing import override, TypeVar
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator, Page

from tests.gui_e2e.testlib.playwright.dropdown import DropdownHelper, DropdownOptions
from tests.gui_e2e.testlib.playwright.helpers import CmkCredentials, DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


TOptions = TypeVar("TOptions", bound=StrEnum)


class EncryptionType(DropdownOptions):
    """Encryption type DropdownOptions the site connection."""

    TLS = "Encrypt data using TLS"
    NONE = "Plain text (Unencrypted)"


class ReplicationType(DropdownOptions):
    """Replication type for the site connection."""

    NO_REPLICATION = "No replication with this site"
    PUSH_CONFIGURATION = "Push configuration to this site"


class DistributedMonitoring(CmkPage):
    """Represent the page `Setup -> General -> Distributed monitoring`."""

    page_title = "Distributed monitoring"

    @override
    def navigate(self) -> None:
        """Instructions to navigate to `Setup -> General -> Distributed monitoring` page."""
        logger.info(f"Navigate to '{self.page_title}' page")
        self.main_menu.setup_menu(self.page_title).click()
        _url_pattern: str = quote_plus("wato.py?mode=sites")
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info(f"Validate that current page is '{self.page_title}' page")
        self.main_area.check_page_title(self.page_title)
        expect(
            self.add_connection_button,
            message=f"Expected 'Add connection' button to be visible on page '{self.page_title}'",
        ).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def data_table(self) -> Locator:
        """The data table containing the site connections."""
        return self.main_area.locator("table.data")

    @property
    def add_connection_button(self) -> Locator:
        """The button to add a new connection."""
        return self.main_area.page_menu_bar.get_by_role("link", name="Add connection")

    def _get_table_row(self, site_id: str) -> Locator:
        """Get the table row for a specific site ID.

        Args:
            site_id: The ID of the site to find.
        """
        return self.data_table.get_by_role("row").filter(
            has=self.main_area.locator().get_by_role("cell", name=site_id, exact=True)
        )

    def get_login_button(self, site_id: str) -> Locator:
        """Get the button to login to the remote site.

        Args:
            site_id: The ID of the site to login to.
        """
        return self._get_table_row(site_id).get_by_role("link", name="Login")

    def add_new_connection(self, remote_site: Site) -> None:
        """Add a new connection to the remote site.

        Args:
            remote_site: The remote site to add.
        """
        logger.info("Add a new connection to the remote site: '%s'", remote_site)
        self.add_connection_button.click()
        add_site_connection_page = AddSiteConnection(self.page, navigate_to_page=False)
        add_site_connection_page.fill_site_connection_form(remote_site)
        add_site_connection_page.save_button.click()

    def check_site_online_status(self, site_id: str) -> None:
        """Check via the UI that the remote site is online.

        Args:
            site_id: The ID of the site to check.
        """
        logger.info(f"Check via the UI that the remote site '{site_id}' is online")
        site_status = self.data_table.locator(f"div#livestatus_status_{site_id}")
        expect(
            site_status,
            message=(
                f"Status of remote site '{site_id}' is not Online in the UI; "
                f"actual status = '{site_status.text_content()}'"
            ),
        ).to_have_text("Online")

    def clean_all_site_connections(self) -> int:
        """Delete all site connections.

        Returns:
            The number of deleted site connections.
        """
        logger.info("Delete all site connections")

        delete_buttons = self.data_table.get_by_role("link", name="Delete")

        number_of_deleted_sites = delete_buttons.count()

        while delete_buttons.count():
            delete_button = delete_buttons.first
            site_id = delete_button.locator("../..").locator("td").nth(1).text_content()
            assert site_id is not None, "Site ID not found"
            delete_button.click()
            self.main_area.get_confirmation_popup_button("Delete").click()
            expect(
                self._get_table_row(site_id), message=f"Site connection '{site_id}' not deleted"
            ).to_have_count(0)

        return number_of_deleted_sites

    def login_to_remote_site(self, remote_site: Site, credentials: CmkCredentials) -> None:
        """Login to the remote site.

        Args:
            remote_site: The remote site to login to.
            credentials: The credentials for the remote site.
        """
        logger.info("Login to the remote site")
        self.get_login_button(remote_site.id).click()
        login_page = LoginRemoteSite(self.page, remote_site, navigate_to_page=False)
        login_page.fill_login_form(credentials)
        login_page.login_button.click()

    def site_specific_global_configuration(self, site_id: str) -> Locator:
        """Configure the site-specific global settings"""
        return self.main_area.locator(f"a[href*='mode=edit_site_globals&site={site_id}']")

    def is_remote_site_licensed(self, site_id: str) -> bool | None:
        """Check if a remote site is licensed.

        Returns None if the replication is disabled (and therefore the license state is unknown).
        Returns a boolean indicating the license state otherwise.
        """
        if "not enabled" in self._get_table_row(site_id).inner_text().lower():
            logger.info(
                'Replication disabled for remote site "%s"; licensing status unknown!', site_id
            )
            return None
        remote_site_license_info = (
            self._get_table_row(site_id).get_by_role("cell").filter(has_text="license state")
        )
        licensed = "license state: licensed" in remote_site_license_info.inner_text().lower()

        return licensed


class AddSiteConnection(CmkPage):
    """Represent the page `Setup -> General -> Distributed monitoring -> Add site connection`."""

    page_title = "Add site connection"

    @override
    def navigate(self) -> None:
        """Instructions to navigate to
        `Setup -> General -> Distributed monitoring -> Add site connection` page.
        """
        logger.info(f"Navigate to '{self.page_title}' page")
        _distributed_monitoring = DistributedMonitoring(self.page)
        _distributed_monitoring.add_connection_button.click()
        _url_pattern: str = quote_plus("wato.py?mode=edit_site")
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info(f"Validate that current page is '{self.page_title}' page")
        self.main_area.check_page_title(self.page_title)
        expect(
            self.site_id_input, message=f"Site ID input not present in '{self.page_title}' page"
        ).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def save_button(self) -> Locator:
        """The button to save the new site connection."""
        return self.main_area.get_suggestion("Save")

    @property
    def form_site(self) -> Locator:
        """The form to add a new site connection."""
        return self.main_area.locator("form#form_site")

    @property
    def site_id_input(self) -> Locator:
        """The input field for the site ID."""
        return self.form_site.locator("input[name='site_p_id']")

    @property
    def site_alias_input(self) -> Locator:
        """The input field for the site alias."""
        return self.form_site.locator("input[name='site_p_alias']")

    @property
    def connection_tcp_host_input(self) -> Locator:
        """The input field for the site host."""
        return self.form_site.locator("input[name='site_p_socket_1_p_address_0']")

    @property
    def connection_tcp_port_input(self) -> Locator:
        """The input field for the site port."""
        return self.form_site.locator("input[name='site_p_socket_1_p_address_1']")

    @property
    def connection_encryptor_dropdown(self) -> DropdownHelper[EncryptionType]:
        """The dropdown for the encryption setting."""
        connection_encryption_selector = self.form_site.get_by_role("combobox").filter(
            has=self.locator("#select2-site_p_socket_1_p_tls_sel-container")
        )
        connection_encryption_options = self.main_area.locator(
            "ul#select2-site_p_socket_1_p_tls_sel-results"
        )
        return DropdownHelper[EncryptionType](
            "Encryption", connection_encryption_selector, connection_encryption_options
        )

    @property
    def url_prefix_input(self) -> Locator:
        """The input field for the URL prefix."""
        return self.form_site.locator("input[name='site_p_url_prefix']")

    @property
    def replication_type_dropdown(self) -> DropdownHelper[ReplicationType]:
        """The dropdown for the replication setting."""
        replication_type_selector = self.form_site.get_by_role("combobox").filter(
            has=self.locator("#select2-site_p_replication-container")
        )
        replication_type_options = self.main_area.locator("ul#select2-site_p_replication-results")
        return DropdownHelper[ReplicationType](
            "Replication", replication_type_selector, replication_type_options
        )

    @property
    def message_broker_port_input(self) -> Locator:
        """The input field for the message broker port."""
        return self.form_site.locator("input[name='site_p_message_broker_port']")

    @property
    def url_of_remote_site_input(self) -> Locator:
        """The input field for the URL of the remote site."""
        return self.form_site.locator("input[name='site_p_multisiteurl']")

    def fill_site_connection_form(self, remote_site: Site) -> None:
        """Fill the form to add a new site connection.

        Args:
            remote_site: The remote site to add.
        """
        logger.info("Fill the form to add a new site connection")
        self.site_id_input.fill(remote_site.id)
        self.site_alias_input.fill(remote_site.alias)
        self.connection_tcp_host_input.fill(remote_site.http_address)
        self.connection_tcp_port_input.fill(str(remote_site.livestatus_port))
        self.connection_encryptor_dropdown.select_option(EncryptionType.NONE)
        self.url_prefix_input.fill(remote_site.url_prefix)
        self.replication_type_dropdown.select_option(ReplicationType.PUSH_CONFIGURATION)
        self.message_broker_port_input.fill(str(remote_site.message_broker_port))
        self.url_of_remote_site_input.fill(remote_site.internal_url)


class LoginRemoteSite(CmkPage):
    """Represents the page `Login to remote site`."""

    page_title_template = 'Login into site "{remote_site_name}"'

    def __init__(self, page: Page, remote_site: Site, navigate_to_page: bool = True) -> None:
        """Initialize the login page for the remote site.

        Args:
            page: The Playwright page object.
            remote_site: The remote site to login to.
            navigate_to_page: Whether to navigate to the page or not.
        """
        self.__remote_site_id = remote_site.id
        self.page_title = self.page_title_template.format(remote_site_name=remote_site.alias)
        super().__init__(page, navigate_to_page=navigate_to_page)

    @override
    def navigate(self) -> None:
        """Instructions to navigate to
        `Setup -> General -> Distributed monitoring -> Login` page.
        """
        logger.info("Navigate to '%s' page", self.page_title)
        _distributed_monitoring = DistributedMonitoring(self.page)
        _distributed_monitoring.get_login_button(self.__remote_site_id).click()
        _url_pattern = re.compile(
            quote_plus("wato.py?") + r".*" + quote_plus(f"_login={self.__remote_site_id}")
        )
        self.page.wait_for_url(url=_url_pattern, wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def form_login(self) -> Locator:
        """The login form."""
        return self.main_area.locator("form#form_login")

    @property
    def username_input(self) -> Locator:
        """The input field for the username."""
        return self.form_login.locator("input[name='_name']")

    @property
    def password_input(self) -> Locator:
        """The input field for the password."""
        return self.form_login.locator("input[name='_passwd']")

    @property
    def confirm_checkbox(self) -> Locator:
        """The checkbox for the confirmation."""
        return self.form_login.locator("label[for='cb__confirm']")

    @property
    def is_checkbox_checked(self) -> bool:
        """The state of the confirmation checkbox."""
        return self.form_login.locator("input[name='_confirm']").is_checked()

    @property
    def login_button(self) -> Locator:
        """The button to login."""
        return self.form_login.locator("#_do_login")

    def fill_login_form(self, credentials: CmkCredentials) -> None:
        """Fill the login form.

        Args:
            credentials: The credentials for the remote site.
        """
        logger.info("Fill the login form")
        self.username_input.fill(credentials.username)
        self.password_input.fill(credentials.password)
        if not self.is_checkbox_checked:
            self.confirm_checkbox.click()
