#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import override

from playwright.sync_api import expect, Locator

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.page import CmkPage
from tests.system.gui.testlib.playwright.pom.setup.otel.alerts import Alerts

logger = logging.getLogger(__name__)


class AddAlert(CmkPage):
    """Represent the page `Setup -> Events -> Alerts -> Add alert`.

    Hosts the creation wizard. Only its first step, naming the alert and selecting the
    custom services it applies to, is implemented; the threshold step is a placeholder.
    """

    page_title = "Add alert"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        alerts_page = Alerts(self.page)
        self.click_and_wait_for_navigation(
            alerts_page.add_alert_button,
            frame_url=re.compile("mode=create_otel_alert"),
        )
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def alert_name_input(self) -> Locator:
        return self.main_area.locator().get_by_role("textbox", name=re.compile("Alert name"))

    @property
    def service_name_select(self) -> Locator:
        return self.main_area.locator().get_by_role("combobox", name="Service name", exact=True)

    @property
    def match_type_select(self) -> Locator:
        return self.main_area.locator().get_by_role(
            "combobox", name="Match service name by", exact=True
        )

    @property
    def next_step_button(self) -> Locator:
        return self.main_area.locator().get_by_role("button", name="Next step")

    @property
    def threshold_step_content(self) -> Locator:
        return self.main_area.locator().get_by_text(
            re.compile("Defining the threshold and saving the alert")
        )

    @property
    def _open_suggestions(self) -> Locator:
        """The option list of the currently open dropdown.

        The dropdown teleports it to the document body, which `main_area` covers.
        """
        return self.main_area.locator().get_by_role("listbox")

    def select_service_name(self, name: str) -> None:
        """Choose a discovered service name, or commit `name` as typed if none matches."""
        logger.info("Select service name '%s'", name)
        self.service_name_select.click()
        self._open_suggestions.get_by_role("textbox", name="filter").fill(name)
        self._open_suggestions.get_by_role("option", name=name, exact=True).click()
        expect(
            self.service_name_select,
            message=f"Service name '{name}' was not selected",
        ).to_contain_text(name)
