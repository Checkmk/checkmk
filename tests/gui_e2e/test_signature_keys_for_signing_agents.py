#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Callable

import pytest
from playwright.sync_api import expect, FilePayload

from tests.testlib.playwright.helpers import PPage

from cmk.utils.crypto import HashAlgorithm
from cmk.utils.crypto.certificate import CertificateWithPrivateKey
from cmk.utils.crypto.password import Password


def go_to_signature_page(page: PPage) -> None:
    """go to the `Signature keys for signing agents` page
    I haven't found a easier way, so here we go..."""
    page.megamenu_setup.click()
    page.main_menu.get_text("Windows, Linux, Solaris, AIX").click()
    page.main_area.locator("#page_menu_dropdown_agents >> text=Agents >> visible=true").click()
    page.main_area.get_text("Signature keys").click()
    page.main_area.check_page_title("Signature keys for signing agents")


def delete_key(page: PPage, identifier: str) -> None:
    """Delete a key based on some text, e.g. alias or hash

    you already have to be on the `Signature keys for signing agents` site
    """

    page.main_area.locator(
        f"tr.data:has-text('{identifier}') >> td.buttons >> a[title='Delete this key']"
    ).click()
    page.main_area.locator("#page_menu_popups").locator("button.swal2-confirm").click()


def send_pem_content(page: PPage, description: str, password: str, content: str) -> None:
    """upload a combined pem file (private key and certificate) via the Paste textarea method"""
    go_to_signature_page(page)
    page.main_area.get_suggestion("Upload key").click()
    page.main_area.check_page_title("Upload agent signature key")
    page.main_area.get_input("key_p_alias").fill(description)
    page.main_area.get_input("key_p_passphrase").fill(password)
    page.main_area.locator("#select2-key_p_key_file_sel-container").click()
    page.main_area.get_text("Paste PEM Content").click()
    page.main_area.locator("textarea[name='key_p_key_file_1']").fill(content)
    page.main_area.get_suggestion("Upload").click()


def send_pem_file(page: PPage, description: str, password: str, content: str) -> None:
    """upload a combined pem file (private key and certificate) via upload"""
    go_to_signature_page(page)
    page.main_area.get_suggestion("Upload key").click()
    page.main_area.check_page_title("Upload agent signature key")
    page.main_area.get_input("key_p_alias").fill(description)
    page.main_area.get_input("key_p_passphrase").fill(password)
    page.main_area.get_input("key_p_key_file_0").set_input_files(
        files=[FilePayload(name="mypem", mimeType="text/plain", buffer=content.encode())]
    )
    page.main_area.get_suggestion("Upload").click()


@pytest.mark.parametrize("upload_function", (send_pem_content, send_pem_file))
def test_upload_signing_keys(
    upload_function: Callable[[PPage, str, str, str], None], logged_in_page: PPage
) -> None:
    """send a few payloads to the `Signature keys for signing agents` page and check the responses"""

    # pem is invalid
    upload_function(logged_in_page, "Some description", "password", "invalid")
    logged_in_page.main_area.check_error("The file does not look like a valid key file.")

    key_pair = CertificateWithPrivateKey.generate_self_signed("Some CN", "e2etest")

    # This is very delicate...
    # But will be fixed soon
    pem_content = (
        key_pair.private_key.dump_pem(Password("SecureP4ssword")).str
        + "\n"
        + key_pair.certificate.dump_pem().str
    ).strip() + "\n"
    fingerprint = key_pair.certificate.fingerprint(HashAlgorithm.MD5).hex(":")

    # passphrase is invalid
    upload_function(logged_in_page, "Some description", "password", pem_content)
    logged_in_page.main_area.check_error("Invalid pass phrase")

    # all ok
    upload_function(logged_in_page, "Some description", "SecureP4ssword", pem_content)
    expect(logged_in_page.main_area.get_text(fingerprint))
    delete_key(logged_in_page, fingerprint)


def test_add_key(logged_in_page: PPage) -> None:
    """add a key, aka let Checkmk generate it"""
    # alias = "An alias"
    go_to_signature_page(logged_in_page)
    logged_in_page.main_area.get_suggestion("Add key").click()
    logged_in_page.main_area.check_page_title("Add agent signature key")

    # Use a too short password
    logged_in_page.main_area.get_input("key_p_alias").fill("Won't work")
    logged_in_page.main_area.get_input("key_p_passphrase").fill("short")
    logged_in_page.main_area.get_suggestion("Create").click()
    logged_in_page.main_area.check_error("You need to provide at least 8 characters.")

    logged_in_page.main_area.get_input("key_p_alias").fill("e2e-test")
    logged_in_page.main_area.get_input("key_p_passphrase").fill("12345678")
    logged_in_page.main_area.get_suggestion("Create").click()
    expect(logged_in_page.main_area.get_text("e2e-test"))

    delete_key(logged_in_page, "e2e-test")
