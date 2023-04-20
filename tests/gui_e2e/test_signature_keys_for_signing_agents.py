#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from typing import Callable

import pytest
from playwright.sync_api import expect, FilePayload

from tests.testlib.playwright.helpers import PPage

from cmk.utils.crypto import HashAlgorithm
from cmk.utils.crypto.certificate import CertificateWithPrivateKey
from cmk.utils.crypto.password import Password


@pytest.fixture(name="self_signed_cert", scope="module")
def fixture_self_signed() -> CertificateWithPrivateKey:
    return CertificateWithPrivateKey.generate_self_signed("Some CN", "e2etest")


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
    logged_in_page: PPage,
    self_signed_cert: CertificateWithPrivateKey,
    upload_function: Callable[[PPage, str, str, str], None],
) -> None:
    """send a few payloads to the `Signature keys for signing agents` page and check the responses"""

    # pem is invalid
    upload_function(logged_in_page, "Some description", "password", "invalid")
    logged_in_page.main_area.check_error("The file does not look like a valid key file.")

    # This is very delicate...
    # But will be fixed soon
    pem_content = (
        self_signed_cert.private_key.dump_pem(Password("SecureP4ssword")).str
        + "\n"
        + self_signed_cert.certificate.dump_pem().str
    ).strip() + "\n"
    fingerprint = self_signed_cert.certificate.fingerprint(HashAlgorithm.MD5).hex(":")

    # passphrase is invalid
    upload_function(logged_in_page, "Some description", "password", pem_content)
    logged_in_page.main_area.check_error("Invalid pass phrase")

    # all ok
    upload_function(logged_in_page, "Some description", "SecureP4ssword", pem_content)
    expect(logged_in_page.main_area.get_text(fingerprint))
    delete_key(logged_in_page, fingerprint)


def test_add_key(logged_in_page: PPage) -> None:
    """add a key, aka let Checkmk generate it"""
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


@pytest.fixture(name="with_key")
def with_key_fixture(
    logged_in_page: PPage, self_signed_cert: CertificateWithPrivateKey
) -> Iterator[None]:
    """create a signing key via the gui, yield and then delete it again"""

    password = Password("foo")
    combined_file = (
        self_signed_cert.private_key.dump_pem(password).str
        + self_signed_cert.certificate.dump_pem().str
    )
    send_pem_file(logged_in_page, "with_key_fixture", password.raw, combined_file)
    expect(logged_in_page.main_area.get_text("with_key_fixture"))

    yield

    logged_in_page.go("index.py?start_url=wato.py%3Ffolder%3D%26mode%3Dsignature_keys")
    delete_key(logged_in_page, "with_key_fixture")


@pytest.mark.xfail(reason="Test flaky, must be investigated")
def test_bake_and_sign(logged_in_page: PPage, with_key: None) -> None:
    """go to agents and click bake and sign

    Bake and sign starts a backgroundjob. If the job finished the success is
    reported. This is kind of asynchronous. Theoretically this could lead to
    timeout problems, but in my experience the signing is quite fast. But if
    this happens restart or mark this test to be skipped"""

    # We need to "waste" some time here. The bake and sign button is sometimes
    # not available if you go too fast to this site.
    logged_in_page.megamenu_setup.click()
    logged_in_page.main_menu.get_text("Windows, Linux, Solaris, AIX").click()
    logged_in_page.main_area.get_suggestion("Bake and sign agents").click()
    logged_in_page.main_area.locator("#select2-key_p_key-container").click()
    logged_in_page.main_area.locator(
        "#select2-key_p_key-results > li.select2-results__option[role='option']"
    ).filter(has_text="with_key_fixture").click()
    logged_in_page.main_area.get_text("with_key_fixture").click()
    logged_in_page.main_area.get_input("key_p_passphrase").fill("foo")
    logged_in_page.main_area.get_input("create").click()
    logged_in_page.main_area.check_success("Agent baking successful")
