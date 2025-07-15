#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time
from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import expect

from cmk.crypto.certificate import CertificateWithPrivateKey
from cmk.crypto.hash import HashAlgorithm
from cmk.crypto.password import Password
from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard
from tests.gui_e2e.testlib.playwright.pom.setup.agent_bakery import AgentBakeryPage
from tests.gui_e2e.testlib.playwright.pom.setup.signature_keys import (
    AddSignatureKeyPage,
    SignatureKeysPage,
    UploadSignatureKeyPage,
)
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


@pytest.fixture(name="self_signed_cert", scope="module")
def fixture_self_signed() -> CertificateWithPrivateKey:
    return CertificateWithPrivateKey.generate_self_signed(
        common_name="Some CN", organization="e2etest", key_size=1024
    )


def send_pem_content(page: Dashboard, description: str, password: str, content: str) -> None:
    """Upload a combined pem file (private key and certificate) via the Paste textarea method."""
    upload_key_page = UploadSignatureKeyPage(page.page)
    upload_key_page.upload_key_pem_content(description, password, content)


def send_pem_file(page: Dashboard, description: str, password: str, content: str) -> None:
    """Upload a combined pem file (private key and certificate) via upload."""
    upload_key_page = UploadSignatureKeyPage(page.page)
    upload_key_page.upload_key_pem_file(description, password, content)


def wait_for_bakery(test_site: Site, max_attempts: int = 60) -> None:
    """Continously check the baking status and return once the agent baking is finished."""
    for attempt in range(max_attempts):
        if test_site.openapi.agents.get_baking_status().state == "finished":
            logger.info("Agent baking completed!")
            return
        assert attempt < max_attempts - 1, "Agent baking timed out!"
        time.sleep(1)


@pytest.mark.parametrize("upload_function", (send_pem_content, send_pem_file))
def test_upload_signing_keys(
    dashboard_page: Dashboard,
    self_signed_cert: CertificateWithPrivateKey,
    upload_function: Callable[[SignatureKeysPage, str, str, str], None],
) -> None:
    """Send a few payloads to the `Signature keys for signing agents` page.

    Also, check the responses.
    """
    signature_keys_page = SignatureKeysPage(dashboard_page.page)
    try:
        # pem is invalid
        upload_function(signature_keys_page, "invalid-1", "password", "invalid")
        signature_keys_page.check_invalid_key_error()

        # This is very delicate...
        pem_content = (
            self_signed_cert.private_key.dump_pem(Password("SecureP4ssword")).str
            + "\n"
            + self_signed_cert.certificate.dump_pem().str
        ).strip() + "\n"
        # passphrase is invalid
        signature_keys_page.navigate()
        upload_function(signature_keys_page, "invalid-2", "password", pem_content)
        signature_keys_page.check_invalid_key_error()

        # all ok
        signature_keys_page.navigate()
        fingerprint = rf"{self_signed_cert.certificate.fingerprint(HashAlgorithm.MD5).hex(':')}"
        upload_function(signature_keys_page, "valid", "SecureP4ssword", pem_content)
        signature_keys_page.ensure_key_uploaded(fingerprint)
    finally:
        signature_keys_page.delete_key()


def test_generate_key(dashboard_page: Dashboard) -> None:
    """Add a key, aka let Checkmk generate it."""
    add_key_page = AddSignatureKeyPage(dashboard_page.page)

    invalid_key = "Won't work"
    valid_key = "e2e-test"

    try:
        # Invalid key: Use a too short password
        add_key_page.fill_key_form(invalid_key, "short")
        add_key_page.main_area.check_error("You need to provide at least 12 characters.")

        # Valid key
        add_key_page.fill_key_form(valid_key, "123456789012")
        expect(
            add_key_page.main_area.get_text(valid_key),
            f"Unable to find the key '{valid_key}' in the list of keys (the main area).",
        ).to_be_visible()
    finally:
        add_key_page.delete_all_keys()


@pytest.fixture(name="with_key", scope="function")
def with_key_fixture(
    dashboard_page: Dashboard, self_signed_cert: CertificateWithPrivateKey
) -> Iterator[str]:
    """Create a signature key via the GUI, yield and then delete it again."""
    key_name = "with_key_fixture"
    password = Password("foo")
    combined_file = (
        self_signed_cert.private_key.dump_pem(password).str
        + self_signed_cert.certificate.dump_pem().str
    )
    try:
        upload_key_page = UploadSignatureKeyPage(dashboard_page.page)
        upload_key_page.upload_key_pem_file(key_name, password.raw, combined_file)
        expect(
            dashboard_page.main_area.get_text(key_name),
            f"Creation of signature key '{key_name}' failed.",
        ).to_be_visible()
        yield key_name
    finally:
        SignatureKeysPage(dashboard_page.page).delete_key(key_name)


def test_download_key(dashboard_page: Dashboard, with_key: str) -> None:
    """Test downloading a key.

    First a wrong password is provided, checking the error message;
    then the key should be downloaded successfully using the correct password.
    """
    signature_keys_page = SignatureKeysPage(dashboard_page.page)
    signature_keys_page.download_key_button.click()

    signature_keys_page.fill_download_key("definitely_wrong")
    signature_keys_page.download_button.click()
    signature_keys_page.main_area.check_error("Invalid pass phrase")

    signature_keys_page.fill_download_key("foo")
    with signature_keys_page.page.expect_download() as download_info:
        signature_keys_page.download_button.click()
    assert download_info.is_done(), (
        "Signature key couldn't be downloaded, even after providing correct passphrase."
    )


def test_bake_and_sign(test_site: Site, dashboard_page: Dashboard, with_key: str) -> None:
    """Go to agents and click "bake and sign."""
    agent_bakery_page = AgentBakeryPage(dashboard_page.page)
    agent_bakery_page.bake_and_sign(with_key, "foo")
    # wait (just in case the bakery is busy)
    wait_for_bakery(test_site)
    agent_bakery_page.bake_and_sign_button.click()
    # wait for completion and verify status
    wait_for_bakery(test_site)
    agent_bakery_page.assert_baking_succeeded()


def test_bake_and_sign_disabled(dashboard_page: Dashboard) -> None:
    """Delete all keys, go to agents and check that the sign buttons are disabled."""
    signature_keys_page = SignatureKeysPage(dashboard_page.page)
    signature_keys_page.delete_all_keys()
    agent_bakery_page = AgentBakeryPage(dashboard_page.page)
    agent_bakery_page.check_sign_buttons_disabled()
