#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
import time
from typing import Any, override
from urllib.parse import quote_plus

from playwright.sync_api import expect, FilePayload, Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.gui_e2e.testlib.playwright.timeouts import TIMEOUT_ASSERTIONS
from tests.testlib.common.utils import wait_until

logger = logging.getLogger(__name__)


class SignatureKeysPage(CmkPage):
    page_title: str = "Signature keys for signing agents"

    @property
    def menu_agents_button(self) -> Locator:
        return self.main_area.locator("#page_menu_dropdown_agents")

    @property
    def menu_agents_content(self) -> Locator:
        return self.main_area.locator("div[id='menu_agents']")

    @property
    def signature_keys_menu_item(self) -> Locator:
        return self.get_link("Signature keys")

    @property
    def upload_key_button(self) -> Locator:
        return self.main_area.get_suggestion("Upload key")

    @property
    def choose_file_button(self) -> Locator:
        return self.main_area.get_input("key_p_key_file_0")

    @property
    def key_passphrase_input(self) -> Locator:
        return self.main_area.get_input("key_p_passphrase")

    @property
    def key_description_input(self) -> Locator:
        return self.main_area.get_input("key_p_alias")

    @property
    def download_button(self) -> Locator:
        return self.main_area.get_suggestion("Download")

    @property
    def download_key_button(self) -> Locator:
        return self.get_link("Download this key")

    @property
    def upload_button(self) -> Locator:
        return self.main_area.get_suggestion("Upload")

    @property
    def confirm_delete_button(self) -> Locator:
        return self.main_area.locator().get_by_role("dialog").get_by_role("button", name="Delete")

    @property
    def create_key_button(self) -> Locator:
        return self.main_area.get_suggestion("Create")

    def _ensure_agents_menu_content_visible(self) -> None:
        """
        Flake-proofing: interaction with 'Agents menu' is unreliable.
        """
        wait_until(
            lambda: (
                self.menu_agents_button.click(),  # type: ignore[func-returns-value]
                time.sleep(0.1),  # type: ignore[func-returns-value]
                self.menu_agents_content.is_visible(),
            )[2],
            interval=1,
            timeout=TIMEOUT_ASSERTIONS,
        )

    def _navigate_to_signature_keys(self) -> None:
        """Navigate to the 'Signature keys for signing agents' page."""
        os_list_menu_item = "Windows, Linux, Solaris, AIX"

        logger.info("Navigate to '%s' / Agent bakery page.", os_list_menu_item)
        self.main_menu.setup_menu(os_list_menu_item).click()
        self.page.wait_for_url(re.compile(quote_plus("wato.py?mode=agents")), wait_until="load")
        self.main_area.check_page_title(os_list_menu_item)

        logger.info("Navigate to '%s' page.", self.page_title)
        self._ensure_agents_menu_content_visible()
        self.signature_keys_menu_item.click()

    @override
    def navigate(self) -> None:
        self._navigate_to_signature_keys()
        self.validate_page()

    @override
    def validate_page(self) -> None:
        self.page.wait_for_url(
            re.compile(quote_plus("wato.py?folder=&mode=signature_keys")), wait_until="load"
        )
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def fill_key_form(self, description: str, password: str) -> None:
        self.key_description_input.fill(description)
        self.key_passphrase_input.fill(password)
        self.create_key_button.click()

    def fill_download_key(self, password: str) -> Any:
        self.key_passphrase_input.fill(password)

    def delete_key(self, identifier: str | None = None) -> None:
        """
        Delete a key, if key identifier is provided. Otherwise, delete all the listed keys.

        Args:
            identifier (str | None): The identifier of the key to delete. The identifier
            can be a key description or a fingerprint. If None, all keys will be deleted.

        Note: you already have to be on the page
        `Setup > Windows, Linux, ... > Signature keys for signing agents`
        """

        def _delete_key(row: Locator) -> None:
            key_identifier = identifier if identifier else row.inner_text().replace("\t", " ")
            logger.info("Deleting key: '%s'!", key_identifier)
            row.get_by_role("link", name="Delete this key").click()
            self.confirm_delete_button.click()
            expect(row, f"Key: '{key_identifier}' not deleted from the list!").to_have_count(0)

        if identifier:
            key_to_delete = self.main_area.locator(f"tr.data:has-text('{identifier}')")
            _delete_key(key_to_delete)
        else:
            rows = self.main_area.locator("tr.data").all()
            if not rows:
                logger.info("There are no keys available. Skip deletion ...")
            # delete the listed keys, if any.
            for row in rows:
                _delete_key(row)

    def delete_all_keys(self) -> None:
        self.delete_key(None)

    def check_invalid_key_error(self) -> None:
        self.main_area.check_error("The key file is invalid or the password is wrong.")

    def ensure_key_uploaded(self, fingerprint: str) -> None:
        expect(
            self.main_area.get_text(fingerprint.upper()),
            f"Previously uploaded signature key '{fingerprint.upper()[:10]}...' not found.",
        ).to_be_visible()


class AddSignatureKeyPage(SignatureKeysPage):
    """Page for adding an agent signature key."""

    page_title = "Add agent signature key"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page.", self.page_title)
        # Navigate to the 'Signature keys for signing agents' page first.
        self._navigate_to_signature_keys()
        self.main_area.get_suggestion("Generate key").click()
        self.page.wait_for_url(
            re.compile(quote_plus("wato.py?mode=edit_signature_key")), wait_until="load"
        )

    @override
    def validate_page(self) -> None:
        logger.info("Validate '%s' page.", self.page_title)
        self.main_area.check_page_title(self.page_title)


class UploadSignatureKeyPage(SignatureKeysPage):
    """Page for uploading an agent signature key."""

    page_title: str = "Upload agent signature key"

    @property
    def upload_pem_file_dropdown(self) -> Locator:
        return self.main_area.locator("#select2-key_p_key_file_sel-container")

    @property
    def paste_pem_contents_option(self) -> Locator:
        return self.main_area.get_text("Paste CRT/PEM Contents")

    @property
    def pem_content_textarea(self) -> Locator:
        return self.main_area.locator("textarea[name='key_p_key_file_1']")

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page.", self.page_title)
        # Navigate to the 'Signature keys for signing agents' page first.
        self._navigate_to_signature_keys()
        self.upload_key_button.click()
        self.page.wait_for_url(
            re.compile(quote_plus("wato.py?mode=upload_signature_key")), wait_until="load"
        )
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate '%s' page.", self.page_title)
        self.main_area.check_page_title(self.page_title)

    def upload_key_pem_content(self, description: str, password: str, content: str) -> None:
        """Upload a combined pem file (private key and certificate) via the Paste textarea method."""
        self.key_description_input.fill(description)
        self.key_passphrase_input.fill(password)

        self.upload_pem_file_dropdown.click()
        self.paste_pem_contents_option.click()
        self.pem_content_textarea.fill(content)

        logger.info("Upload key '%s'.", description)
        self.upload_button.click()

    def upload_key_pem_file(self, description: str, password: str, content: str) -> None:
        """Upload a combined pem file (private key and certificate) via upload."""
        self.key_description_input.fill(description)
        self.key_passphrase_input.fill(password)
        self.choose_file_button.set_input_files(
            files=[
                FilePayload(
                    name="mypem.pem", mimeType="application/x-x509-ca-cert", buffer=content.encode()
                )
            ]
        )

        logger.info("Upload key '%s'.", description)
        self.upload_button.click()
