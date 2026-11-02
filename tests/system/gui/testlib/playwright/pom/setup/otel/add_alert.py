#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import Literal, override

from playwright.sync_api import expect, Locator

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.graphing.graph_accessor import (
    ENGINE_GRAPH_PANEL_SELECTOR,
)
from tests.system.gui.testlib.playwright.pom.graphing.timeseries_graph import GraphPanel
from tests.system.gui.testlib.playwright.pom.page import CmkPage
from tests.system.gui.testlib.playwright.pom.setup.otel.alerts import Alerts

logger = logging.getLogger(__name__)

type MatchType = Literal["Exact match", "Regular expression"]

type LevelsBound = Literal["Upper", "Lower"]

# The titles of the warning and critical level of each bound, as the levels form shows them.
_LEVEL_TITLES: dict[LevelsBound, tuple[str, str]] = {
    "Upper": ("Warning at", "Critical at"),
    "Lower": ("Warning below", "Critical below"),
}


class AddAlert(CmkPage):
    """Represent the page `Setup -> Events -> Alerts -> Add alert`.

    Hosts the creation wizard: naming the alert, selecting the custom services it
    applies to, then defining its thresholds.
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

    # Every step

    @property
    def active_step(self) -> Locator:
        return self.main_area.locator("ol.cmk-wizard").locator('li[aria-current="step"]')

    def step_heading(self, title: str) -> Locator:
        return self.active_step.get_by_role("heading", name=title, exact=True)

    @property
    def next_step_button(self) -> Locator:
        return self.active_step.get_by_role("button", name="Next step")

    def go_to_next_step(self, heading: str) -> None:
        """Click 'Next step' and wait until the step titled `heading` is open."""
        logger.info("Go to the step '%s'", heading)
        self.next_step_button.click()
        expect(
            self.step_heading(heading), f"The wizard did not move on to the step {heading!r}"
        ).to_be_visible()

    # Step 1: Name the alert

    @property
    def alert_name_input(self) -> Locator:
        return self.main_area.locator().get_by_role("textbox", name=re.compile("Alert name"))

    def complete_name_step(self, name: str) -> None:
        logger.info("Name the alert '%s'", name)
        self.alert_name_input.fill(name)
        self.next_step_button.click()
        expect(
            self.service_name_select, message="The wizard did not move on to the service step"
        ).to_be_visible()

    # Step 2: Select services

    @property
    def service_name_select(self) -> Locator:
        return self.main_area.locator().get_by_role("combobox", name="Service name", exact=True)

    @property
    def match_type_select(self) -> Locator:
        return self.main_area.locator().get_by_role(
            "combobox", name="Match service name by", exact=True
        )

    def select_match_type(self, match_type: MatchType) -> None:
        logger.info("Match the service name by '%s'", match_type)
        self.match_type_select.click()
        self._pick_suggestion(match_type)
        expect(
            self.match_type_select, f"Match type {match_type!r} was not selected"
        ).to_contain_text(match_type)

    def select_service_name(self, name: str) -> None:
        """Choose a discovered service name, or commit `name` as typed if none matches.

        A regular expression is committed as typed, too.
        """
        logger.info("Select service name '%s'", name)
        self.service_name_select.click()
        self._open_suggestions.get_by_role("textbox", name="filter").fill(name)
        self._pick_suggestion(name)
        expect(
            self.service_name_select,
            message=f"Service name '{name}' was not selected",
        ).to_contain_text(name)

    @property
    def folder_select(self) -> Locator:
        return self.active_step.get_by_role("combobox", name="Folder", exact=True)

    def select_folder(self, folder_title: str) -> None:
        """Restrict the alert to the hosts in or below the folder titled `folder_title`.

        The dropdown indents a subfolder below its parent, e.g. "      └─ Folder A".
        """
        logger.info("Select folder '%s'", folder_title)
        self.folder_select.click()
        option = self._open_suggestions.get_by_role(
            "option", name=re.compile(rf"^(\s*└─ )?{re.escape(folder_title)}$")
        )
        expect(option, f"No folder titled {folder_title!r} was offered").to_be_visible()
        option.click()
        expect(self.folder_select, f"Folder {folder_title!r} was not selected").to_contain_text(
            folder_title
        )

    @property
    def matching_services_heading(self) -> Locator:
        """The heading of the matching services, with their count: "Matching services (2)".

        The count gets a "+" when the search stopped at its limit. Shown only once a search
        found services; it re-evaluates whenever the service name or the conditions change.
        """
        return self.active_step.get_by_text(re.compile(r"^Matching services \("))

    @property
    def matching_services(self) -> Locator:
        """One item per matching service, holding its service and host name."""
        return self.active_step.locator(".mode-alerts-services-step__list > li")

    def matching_service(self, service_name: str, host_name: str) -> Locator:
        return self.matching_services.filter(
            has=self.page.get_by_text(service_name, exact=True)
        ).filter(has=self.page.get_by_text(host_name, exact=True))

    @property
    def no_matching_services_message(self) -> Locator:
        return self.active_step.get_by_text(
            "No matching services. Only discovered services can be selected."
        )

    # Step 3: Define threshold

    @property
    def threshold_step_content(self) -> Locator:
        return self.main_area.locator().get_by_text(
            "Set the default levels of the selected custom services."
        )

    @property
    def graph_preview(self) -> GraphPanel:
        """The preview graph of the selected services, with a line per fixed level."""
        return GraphPanel(
            self.active_step.locator(ENGINE_GRAPH_PANEL_SELECTOR), self.page, self.main_area
        )

    def _levels(self, bound: LevelsBound) -> Locator:
        return self.active_step.get_by_role("group", name=f"{bound} levels", exact=True)

    def set_fixed_levels(self, bound: LevelsBound, warning: float, critical: float) -> None:
        """Enable the `bound` levels and set them to fixed warning and critical levels."""
        logger.info("Set fixed %s levels to %s/%s", bound.lower(), warning, critical)
        levels = self._levels(bound)
        levels.get_by_role("checkbox", name=f"{bound} levels", exact=True).check()
        levels_type = levels.get_by_role("combobox", name=f"{bound} levels", exact=True)
        levels_type.click()
        self._pick_suggestion("Fixed levels")
        expect(levels_type, f"Fixed {bound.lower()} levels were not selected").to_contain_text(
            "Fixed levels"
        )
        warning_title, critical_title = _LEVEL_TITLES[bound]
        levels.get_by_role("spinbutton", name=warning_title, exact=True).fill(str(warning))
        levels.get_by_role("spinbutton", name=critical_title, exact=True).fill(str(critical))

    @property
    def create_and_activate_button(self) -> Locator:
        return self.active_step.get_by_role("button", name="Create & activate changes", exact=True)

    def create_alert(self) -> None:
        """Create the alert and follow the wizard to the 'Activate changes' page.

        The alert is created, but the changes are not activated yet.
        """
        logger.info("Create the alert")
        self.click_and_wait_for_navigation(
            self.create_and_activate_button, frame_url=re.compile("mode=changelog")
        )

    # Dropdowns of every step

    @property
    def _open_suggestions(self) -> Locator:
        """The option list of the currently open dropdown.

        The dropdown teleports it to the document body, which `main_area` covers.
        """
        return self.main_area.locator().get_by_role("listbox")

    def _pick_suggestion(self, title: str) -> None:
        option = self._open_suggestions.get_by_role("option", name=title, exact=True)
        expect(option, f"No suggestion titled {title!r} was offered").to_be_visible()
        option.click()
