#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
import time
from collections.abc import Callable, Iterator
from urllib.parse import quote_plus

import pytest
from playwright.sync_api import expect, FilePayload, Locator

from tests.testlib.playwright.pom.dashboard import Dashboard
from tests.testlib.playwright.timeouts import TIMEOUT_ASSERTIONS
from tests.testlib.site import Site
from tests.testlib.utils import wait_until

from cmk.crypto.certificate import CertificateWithPrivateKey
from cmk.crypto.hash import HashAlgorithm
from cmk.crypto.password import Password

logger = logging.getLogger(__name__)


@pytest.fixture(name="self_signed_cert", scope="module")
def fixture_self_signed() -> CertificateWithPrivateKey:
    return CertificateWithPrivateKey.generate_self_signed(
        common_name="Some CN", organization="e2etest", key_size=1024
    )


def go_to_signature_page(page: Dashboard) -> None:
    """Go to the `Signature keys for signing agents` page."""
    logger.info("Navigate to 'Windows, Linux, ...' / Agent bakery page.")
    page.main_menu.setup_menu("Windows, Linux, Solaris, AIX").click()
    page.page.wait_for_url(re.compile(quote_plus("wato.py?mode=agents")))
    page.main_area.check_page_title("Windows, Linux, Solaris, AIX")

    logger.info("Navigate to 'Signature keys for signing agents' page.")

    # flake-proofing: interaction with 'Agents menu' is unreliable.
    def _click_on_agents_menu() -> bool:
        page.main_area.locator("#page_menu_dropdown_agents").click()
        time.sleep(0.1)
        return page.main_area.locator("div[id='menu_agents']").is_visible()

    wait_until(_click_on_agents_menu, interval=1, timeout=TIMEOUT_ASSERTIONS)

    page.get_link("Signature keys").click()
    page.page.wait_for_url(re.compile(quote_plus("wato.py?folder=&mode=signature_keys")))
    page.main_area.check_page_title("Signature keys for signing agents")


def delete_key(page: Dashboard, identifier: str | None = None) -> None:
    """Delete a key, if key identifier is provided. Otherwise, delete all the listed keys.

    `identifier` can be a key description or a fingerprint.

    Note: you already have to be on the page
    `Setup > Windows, Linux, ... > Signature keys for signing agents`
    """

    def _delete_key(row: Locator) -> None:
        key_identifier = identifier if identifier else row.inner_text().replace("\t", " ")
        logger.info("Deleting key: '%s'!", key_identifier)

        row.get_by_role("link", name="Delete this key").click()
        page.main_area.locator().get_by_role("dialog").get_by_role("button", name="Delete").click()
        expect(row, f"Key: '{key_identifier}' not deleted from the list!").to_have_count(0)

    if identifier:
        _delete_key(page.main_area.locator(f"tr.data:has-text('{identifier}')"))
    else:
        rows = page.main_area.locator("tr.data").all()
        if not rows:
            logger.info("There are no keys available. Skip deletion ...")
        # delete the listed keys, if any.
        for row in rows:
            _delete_key(row)


def send_pem_content(page: Dashboard, description: str, password: str, content: str) -> None:
    """Upload a combined pem file (private key and certificate) via the Paste textarea method."""

    _navigate_to_upload_key(page)
    page.main_area.get_input("key_p_alias").fill(description)
    page.main_area.get_input("key_p_passphrase").fill(password)
    page.main_area.locator("#select2-key_p_key_file_sel-container").click()
    page.main_area.get_text("Paste CRT/PEM Contents").click()
    page.main_area.locator("textarea[name='key_p_key_file_1']").fill(content)

    logger.info("Upload key '%s'.", description)
    page.main_area.get_suggestion("Upload").click()


def send_pem_file(page: Dashboard, description: str, password: str, content: str) -> None:
    """Upload a combined pem file (private key and certificate) via upload."""

    _navigate_to_upload_key(page)
    page.main_area.get_input("key_p_alias").fill(description)
    page.main_area.get_input("key_p_passphrase").fill(password)
    page.main_area.get_input("key_p_key_file_0").set_input_files(
        files=[
            FilePayload(
                name="mypem.pem", mimeType="application/x-x509-ca-cert", buffer=content.encode()
            )
        ]
    )

    logger.info("Upload key '%s'.", description)
    page.main_area.get_suggestion("Upload").click()


def _navigate_to_upload_key(page: Dashboard) -> None:
    """Navigate to 'Upload key' page.

    The page can be accessed at
    ```
    Setup
        > Main menu
            > Windows, Linux, ... (Agent bakery)
                > Signature keys for signing agents
    ```             > Upload key
    """
    go_to_signature_page(page)
    # TODO: move to test teardown.
    delete_key(page)

    logger.info("Navigate to 'Upload key' page.")
    page.main_area.get_suggestion("Upload key").click()
    page.page.wait_for_url(re.compile(quote_plus("wato.py?mode=upload_signature_key")))
    page.main_area.check_page_title("Upload agent signature key")


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
    upload_function: Callable[[Dashboard, str, str, str], None],
) -> None:
    """Send a few payloads to the `Signature keys for signing agents` page and check the
    responses."""

    # pem is invalid
    upload_function(dashboard_page, "Some description", "password", "invalid")
    dashboard_page.main_area.check_error("The key file is invalid or the password is wrong.")

    # This is very delicate...
    # But will be fixed soon
    pem_content = (
        self_signed_cert.private_key.dump_pem(Password("SecureP4ssword")).str
        + "\n"
        + self_signed_cert.certificate.dump_pem().str
    ).strip() + "\n"
    fingerprint = rf'{self_signed_cert.certificate.fingerprint(HashAlgorithm.MD5).hex(":")}'

    # passphrase is invalid
    upload_function(dashboard_page, "Some description", "password", pem_content)
    dashboard_page.main_area.check_error("The key file is invalid or the password is wrong.")

    # all ok
    upload_function(dashboard_page, "Some description", "SecureP4ssword", pem_content)
    expect(
        dashboard_page.main_area.get_text(fingerprint.upper()),
        f"Previously uploaded signature key '{fingerprint.upper()[:10]}...' not found.",
    ).to_be_visible()

    delete_key(dashboard_page, fingerprint)


def test_generate_key(dashboard_page: Dashboard) -> None:
    """Add a key, aka let Checkmk generate it."""
    key_name = "e2e-test"
    go_to_signature_page(dashboard_page)

    # TODO: move to test teardown.
    delete_key(dashboard_page)

    dashboard_page.click_and_wait(
        dashboard_page.main_area.get_suggestion("Generate key"), navigate=True
    )
    dashboard_page.main_area.check_page_title("Add agent signature key")

    # Use a too short password
    dashboard_page.main_area.get_input("key_p_alias").fill("Won't work")
    dashboard_page.main_area.get_input("key_p_passphrase").fill("short")
    dashboard_page.main_area.get_suggestion("Create").click()
    dashboard_page.main_area.check_error("You need to provide at least 12 characters.")

    dashboard_page.main_area.get_input("key_p_alias").fill(key_name)
    dashboard_page.main_area.get_input("key_p_passphrase").fill("123456789012")
    dashboard_page.main_area.get_suggestion("Create").click()
    expect(
        dashboard_page.main_area.get_text("e2e-test"),
        "Unable to find the key 'e2e-test' in the list of keys (the main area).",
    ).to_be_visible()

    delete_key(dashboard_page, key_name)


@pytest.fixture(name="with_key")
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
    send_pem_file(dashboard_page, key_name, password.raw, combined_file)
    expect(
        dashboard_page.main_area.get_text(key_name),
        f"Creation of signature key '{key_name}' failed.",
    ).to_be_visible()

    yield key_name

    go_to_signature_page(dashboard_page)
    delete_key(dashboard_page, key_name)


def test_download_key(dashboard_page: Dashboard, with_key: str) -> None:
    """Test downloading a key.

    First a wrong password is provided, checking the error message; then the key should be
    downloaded successfully using the correct password."""
    go_to_signature_page(dashboard_page)

    dashboard_page.get_link("Download this key").click()

    dashboard_page.main_area.get_input("key_p_passphrase").fill("definitely_wrong")
    dashboard_page.main_area.get_suggestion("Download").click()
    dashboard_page.main_area.check_error("Invalid pass phrase")

    dashboard_page.main_area.get_input("key_p_passphrase").fill("foo")
    with dashboard_page.page.expect_download() as download_info:
        dashboard_page.main_area.get_suggestion("Download").click()

    assert (
        download_info.is_done()
    ), "Signature key couldn't be downloaded, even after providing correct passphrase."


def test_bake_and_sign(dashboard_page: Dashboard, test_site: Site, with_key: str) -> None:
    """Go to agents and click "bake and sign."

    "Bake and sign" starts an asynchronous background job, which is why we run "wait_for_bakery()".
    If the job finished, the success is reported and the test can continue."""
    dashboard_page.click_and_wait(
        dashboard_page.main_menu.setup_menu("Windows, Linux, Solaris, AIX"), navigate=True
    )
    dashboard_page.click_and_wait(
        locator=dashboard_page.main_area.get_suggestion("Bake and sign agents"),
        navigate=False,
    )

    dashboard_page.main_area.locator("#select2-key_p_key-container").click()
    dashboard_page.main_area.locator(
        "#select2-key_p_key-results > li.select2-results__option[role='option']"
    ).filter(has_text="with_key_fixture").first.click()
    dashboard_page.main_area.get_text(with_key).click()
    dashboard_page.main_area.get_input("key_p_passphrase").fill("foo")

    # wait (just in case the bakery is busy)
    wait_for_bakery(test_site)
    dashboard_page.click_and_wait(
        locator=dashboard_page.main_area.get_input("create"), navigate=False
    )

    # wait for completion and verify status
    wait_for_bakery(test_site)
    expect(
        dashboard_page.main_area.get_text("Agent baking successful"),
        "Message box with text 'Agent baking successful' was not found.",
    ).to_be_visible()


def test_bake_and_sign_disabled(dashboard_page: Dashboard) -> None:
    """Delete all keys, go to agents and check that the sign buttons are disabled."""
    go_to_signature_page(dashboard_page)
    delete_key(dashboard_page)

    dashboard_page.click_and_wait(
        dashboard_page.main_menu.setup_menu("Windows, Linux, Solaris, AIX"), navigate=True
    )

    expect(
        dashboard_page.main_area.get_suggestion("Bake and sign agents"),
        "The 'bake and sign agents' button should be disabled after key deletion, but isn't.",
    ).to_have_class(re.compile("disabled"))
    expect(
        dashboard_page.main_area.get_suggestion("Sign agents"),
        "The 'sign agents' button should be disabled after key deletion, but isn't.",
    ).to_have_class(re.compile("disabled"))
