#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class CreateRelay(CmkPage):
    """Represent the page 'Add Relay configuration' for creating a new relay.

    Accessible at Setup > Relays > Add Relay configuration.
    """

    page_title = "Add Relay configuration"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to 'Add Relay configuration' page")
        self.main_menu.setup_menu("Relays").click()
        _url_pattern: str = quote_plus("wato.py?mode=relays")
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        self.main_area.get_suggestion("Add Relay configuration").click()
        _url_pattern = quote_plus("wato.py?mode=create_relay")
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is 'Add Relay configuration' page")
        self.main_area.check_page_title(self.page_title)
        expect(self.vue_app).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def vue_app(self) -> Locator:
        """Return the Vue application container."""
        return self.main_area.locator().get_by_role("region", name="Relay configuration wizard")

    @property
    def active_step(self) -> Locator:
        """Return the currently active wizard step."""
        return self.vue_app.locator(".cmk-wizard-step--active")

    @property
    def active_step_heading(self) -> Locator:
        """Return the heading of the active wizard step."""
        return self.active_step.get_by_role("heading", level=2)

    @property
    def active_step_code(self) -> Locator:
        """Return the code block in the active step."""
        return self.active_step.locator("pre code")

    @property
    def next_step_button(self) -> Locator:
        """Return the 'Next step' button in the active step."""
        return self.active_step.get_by_role("button", name="Next step")

    @property
    def previous_step_button(self) -> Locator:
        """Return the 'Previous step' button in the active step."""
        return self.active_step.get_by_role("button", name="Previous step")

    @property
    def relay_alias_input(self) -> Locator:
        """Return the relay alias text input in the Name step."""
        return self.active_step.get_by_role("textbox")

    def os_toggle_button(self, os_name: str) -> Locator:
        """Return the OS toggle button by label (e.g. 'Ubuntu', 'Red Hat')."""
        return self.active_step.get_by_role("button", name=f"Toggle {os_name}")
