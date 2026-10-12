#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import override
from urllib.parse import urljoin

from playwright.sync_api import expect, Locator

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class TrialModeSelection(CmkPage):
    """The trial mode selection dialog.

    Admins get it after login while the site waits for their selection: every GUI page
    redirects to it. It shows one screen at a time, so the locators find the elements
    of the current screen only.
    """

    url_suffix = r"trial_mode_selection.py"

    @override
    def navigate(self) -> None:
        """Open any GUI page and let the site redirect to the dialog."""
        logger.info("Navigate to the trial mode selection dialog")
        self.page.goto(urljoin(self.page.url, "index.py"), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is the trial mode selection dialog")
        expect(self.page).to_have_url(re.compile(self.url_suffix))
        expect(self.heading).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def heading(self) -> Locator:
        return self.page.get_by_role("heading", level=1)

    @property
    def alert(self) -> Locator:
        return self.page.get_by_role("alert")

    def _card(self, title: str) -> Locator:
        return self.page.get_by_role("link", name=re.compile(re.escape(title)))

    def _button(self, label: str) -> Locator:
        return self.page.get_by_role("button", name=label, exact=True)

    @property
    def start_trial_card(self) -> Locator:
        return self._card("Start a trial")

    @property
    def existing_customer_card(self) -> Locator:
        return self._card("I'm an existing customer")

    @property
    def verify_online_card(self) -> Locator:
        return self._card("Verify online")

    @property
    def verify_later_button(self) -> Locator:
        return self._button("Verify later")

    @property
    def email_input(self) -> Locator:
        return self.page.get_by_label("Email address")

    @property
    def send_code_button(self) -> Locator:
        return self._button("Send code")

    @property
    def code_digits(self) -> Locator:
        return self.page.get_by_role("group", name="Verification code").get_by_role("textbox")

    @property
    def resend_code_button(self) -> Locator:
        """Shows a countdown, e.g. "Resend code (0:59)", once a code was sent."""
        return self.page.get_by_role("button", name=re.compile(r"^Resend code"))

    @property
    def verify_button(self) -> Locator:
        return self._button("Verify")

    @property
    def continue_without_verification_button(self) -> Locator:
        return self._button("Continue without verification")

    @property
    def continue_as_offline_trial_button(self) -> Locator:
        return self._button("Continue as offline trial")

    @property
    def start_monitoring_button(self) -> Locator:
        return self._button("Start monitoring")

    def start_trial_and_send_code(self, email: str) -> None:
        """Start a trial and request a verification code for email."""
        self.start_trial_card.click()
        expect(self.heading).to_have_text("Verify your email address")
        self.email_input.fill(email)
        self.send_code_button.click()
        expect(self.heading).to_have_text("Enter your verification code")

    def expect_code_sent(self) -> None:
        """Wait until the site sent the code: the resend countdown starts then."""
        expect(self.resend_code_button).to_have_text(re.compile(r"\(\d+:\d\d\)"))

    def enter_code(self, code: str) -> None:
        """Type the code; the dialog submits it once all digits are in."""
        self.code_digits.first.press_sequentially(code)
