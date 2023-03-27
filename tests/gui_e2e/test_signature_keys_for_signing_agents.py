#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
import time
from collections.abc import Iterator
from typing import Callable, Optional

import pytest
from playwright._impl import _api_types
from playwright.sync_api import expect, FilePayload

from tests.testlib.playwright.helpers import PPage
from tests.testlib.site import Site

from cmk.utils.crypto import HashAlgorithm
from cmk.utils.crypto.certificate import CertificateWithPrivateKey
from cmk.utils.crypto.password import Password

logger = logging.getLogger(__name__)


@pytest.fixture(name="self_signed_cert", scope="module")
def fixture_self_signed() -> CertificateWithPrivateKey:
    return CertificateWithPrivateKey.generate_self_signed("Some CN", "e2etest")


def go_to_signature_page(page: PPage) -> None:
    """Go to the `Signature keys for signing agents` page."""
    page.megamenu_setup.click()
    page.click_and_wait(page.main_menu.get_text("Windows, Linux, Solaris, AIX"), navigate=True)
    page.main_area.locator("#page_menu_dropdown_agents >> text=Agents >> visible=true").click()
    page.click_and_wait(page.main_area.get_text("Signature keys"), navigate=True)
    page.main_area.check_page_title("Signature keys for signing agents")


def delete_key(page: PPage, identifier: Optional[str] = None) -> None:
    """Delete a key based on some text, e.g. alias or hash.

    Note: you already have to be on the `Signature keys for signing agents` site.
    """
    locator = f"tr.data:has-text('{identifier}')" if identifier else "tr.data"
    try:
        for row in page.main_area.locator(f"{locator}").all():
            row.locator("td.buttons >> a[title='Delete this key']").click()
            page.main_area.locator("#page_menu_popups").locator("button.swal2-confirm").click()
    except _api_types.TimeoutError:
        pass


def send_pem_content(page: PPage, description: str, password: str, content: str) -> None:
    """Upload a combined pem file (private key and certificate) via the Paste textarea method."""
    go_to_signature_page(page)
    delete_key(page, description)

    page.click_and_wait(page.main_area.get_suggestion("Upload key"), navigate=True)
    page.main_area.check_page_title("Upload agent signature key")

    page.main_area.get_input("key_p_alias").fill(description)
    page.main_area.get_input("key_p_passphrase").fill(password)
    page.main_area.locator("#select2-key_p_key_file_sel-container").click()
    page.main_area.get_text("Paste PEM Content").click()
    page.main_area.locator("textarea[name='key_p_key_file_1']").fill(content)

    page.main_area.get_suggestion("Upload").click()


def send_pem_file(page: PPage, description: str, password: str, content: str) -> None:
    """Upload a combined pem file (private key and certificate) via upload."""
    go_to_signature_page(page)
    delete_key(page, description)

    page.click_and_wait(page.main_area.get_suggestion("Upload key"), navigate=True)
    page.main_area.check_page_title("Upload agent signature key")

    page.main_area.get_input("key_p_alias").fill(description)
    page.main_area.get_input("key_p_passphrase").fill(password)
    page.main_area.get_input("key_p_key_file_0").set_input_files(
        files=[FilePayload(name="mypem", mimeType="text/plain", buffer=content.encode())]
    )

    page.main_area.get_suggestion("Upload").click()


def wait_for_bakery(test_site: Site, max_attempts: int = 60) -> None:
    """Continously check the baking status and return once the agent baking is finished."""
    for attempt in range(max_attempts):
        if test_site.openapi.get_baking_status().state == "finished":
            logger.info("Agent baking completed!")
            return
        assert attempt < max_attempts - 1, "Agent baking timed out!"
        time.sleep(1)


@pytest.mark.parametrize("upload_function", (send_pem_content, send_pem_file))
def test_upload_signing_keys(
    logged_in_page: PPage,
    self_signed_cert: CertificateWithPrivateKey,
    upload_function: Callable[[PPage, str, str, str], None],
    is_firefox: bool,
) -> None:
    """Send a few payloads to the `Signature keys for signing agents` page and check the
    responses."""

    if is_firefox:
        pytest.xfail(reason="Test flaky when running on the firefox engine.")  # TODO: investigate

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
    expect(logged_in_page.main_area.get_text(fingerprint)).to_be_visible()

    delete_key(logged_in_page, fingerprint)


def test_add_key(logged_in_page: PPage) -> None:
    """Add a key, aka let Checkmk generate it."""
    go_to_signature_page(logged_in_page)
    delete_key(logged_in_page, "e2e-test")

    logged_in_page.click_and_wait(logged_in_page.main_area.get_suggestion("Add key"), navigate=True)
    logged_in_page.main_area.check_page_title("Add agent signature key")

    # Use a too short password
    logged_in_page.main_area.get_input("key_p_alias").fill("Won't work")
    logged_in_page.main_area.get_input("key_p_passphrase").fill("short")
    logged_in_page.main_area.get_suggestion("Create").click()
    logged_in_page.main_area.check_error("You need to provide at least 8 characters.")

    logged_in_page.main_area.get_input("key_p_alias").fill("e2e-test")
    logged_in_page.main_area.get_input("key_p_passphrase").fill("12345678")
    logged_in_page.main_area.get_suggestion("Create").click()
    expect(logged_in_page.main_area.get_text("e2e-test")).to_be_visible()

    delete_key(logged_in_page, "e2e-test")


@pytest.fixture(name="with_key")
def with_key_fixture(
    logged_in_page: PPage, self_signed_cert: CertificateWithPrivateKey
) -> Iterator[str]:
    """Create a signing key via the GUI, yield and then delete it again."""
    key_name = "with_key_fixture"
    password = Password("foo")
    combined_file = (
        self_signed_cert.private_key.dump_pem(password).str
        + self_signed_cert.certificate.dump_pem().str
    )
    send_pem_file(logged_in_page, key_name, password.raw, combined_file)
    expect(logged_in_page.main_area.get_text(key_name)).to_be_visible()

    yield key_name

    delete_key(logged_in_page, key_name)


def test_bake_and_sign(logged_in_page: PPage, test_site: Site, with_key: str) -> None:
    """Go to agents and click bake and sign.

    Bake and sign starts an asynchronous background job, which is why we run "wait_for_bakery()".
    If the job finished, the success is reported and the test can continue."""
    logged_in_page.megamenu_setup.click()
    logged_in_page.click_and_wait(
        logged_in_page.main_menu.get_text("Windows, Linux, Solaris, AIX"), navigate=True
    )
    logged_in_page.click_and_wait(
        locator=logged_in_page.main_area.get_suggestion("Bake and sign agents"),
        navigate=False,
    )

    logged_in_page.main_area.locator("#select2-key_p_key-container").click()
    logged_in_page.main_area.locator(
        "#select2-key_p_key-results > li.select2-results__option[role='option']"
    ).filter(has_text="with_key_fixture").first.click()
    logged_in_page.main_area.get_text(with_key).click()
    logged_in_page.main_area.get_input("key_p_passphrase").fill("foo")

    # wait (just in case the bakery is busy)
    wait_for_bakery(test_site)
    logged_in_page.click_and_wait(
        locator=logged_in_page.main_area.get_input("create"), navigate=False
    )

    # wait for completion and verify status
    wait_for_bakery(test_site)
    expect(logged_in_page.main_area.get_text("Agent baking successful")).to_be_visible(
        timeout=30000
    )


def test_bake_and_sign_disabled(logged_in_page: PPage) -> None:
    """Delete all keys, go to agents and check that the sign buttons are disabled."""
    go_to_signature_page(logged_in_page)
    delete_key(logged_in_page)

    logged_in_page.megamenu_setup.click()
    logged_in_page.click_and_wait(
        logged_in_page.main_menu.get_text("Windows, Linux, Solaris, AIX"), navigate=True
    )

    expect(logged_in_page.main_area.get_suggestion("Bake and sign agents")).to_have_class(
        re.compile("disabled"), timeout=15000
    )
    expect(logged_in_page.main_area.get_suggestion("Sign agents")).to_have_class(
        re.compile("disabled"), timeout=15000
    )
