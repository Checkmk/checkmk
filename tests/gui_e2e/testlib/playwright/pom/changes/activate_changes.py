#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
import time
from re import Pattern
from typing import override

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import LocatorHelper

# from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class ActivateChangesSlideout(LocatorHelper):
    """Represents main menu 'Changes > Activate pending changes' slideout"""

    slide_title: str = "Activate pending changes"

    def __init__(self, cmk_page: CmkPage) -> None:
        self.cmk_page = cmk_page
        logger.info("Navigate to 'Main menu' -> 'Activate pending changes' slideout")
        if not self.title.is_visible():
            self.cmk_page.main_menu.changes_menu().click()
        logger.info("Validate that slideout is %s open", self.slide_title)
        expect(self.title).to_be_visible()

    @override
    def locator(
        self,
        selector: str | None = None,
        *,
        has_text: Pattern[str] | str | None = None,
        has_not_text: Pattern[str] | str | None = None,
        has: Locator | None = None,
        has_not: Locator | None = None,
    ) -> Locator:
        if not selector:
            selector = "xpath=."
        _loc = self.cmk_page.locator("#check_mk_sidebar").locator(selector)
        kwargs = self._build_locator_kwargs(
            has_text=has_text,
            has_not_text=has_not_text,
            has=has,
            has_not=has_not,
        )
        _loc = _loc.filter(**kwargs) if kwargs else _loc
        return _loc

    @property
    def slideout(self) -> Locator:
        return (
            self.cmk_page.locator("#popup_menu_changes div")
            .filter(has_text=self.slide_title)
            .nth(1)
        )

    @property
    def title(self) -> Locator:
        return self.slideout.get_by_role("heading", name=self.slide_title)

    @property
    def activate_changes_btn(self) -> Locator:
        return self.slideout.get_by_role("button", name=self.slide_title)

    @property
    def full_view_btn(self) -> Locator:
        return self.slideout.get_by_role("button", name="Open full view")

    @property
    def no_pending_changes_text(self) -> Locator:
        return self.slideout.get_by_text("No pending changes")

    @property
    def info_text(self) -> Locator:
        return self.slideout.get_by_text("Changes are saved in a")

    @property
    def info_close_btn(self) -> Locator:
        return self.slideout.get_by_role("button", name="Do not show again")

    @property
    def sites_section(self) -> Locator:
        return self.slideout.locator("div.cmk-changes-site-single")

    @property
    def changes_section(self) -> Locator:
        return self.slideout.locator("div.cmk-scroll-pending-changes-container")

    @property
    def total_changes_lbl(self) -> Locator:
        return self.slideout.locator("span.cmk-collapsible-title__text", has_text="Changes:")

    @property
    def foreign_changes_lbl(self) -> Locator:
        return self.slideout.locator(
            "span.cmk-collapsible-title__side-text", has_text="Foreign changes:"
        )

    @property
    def sites_with_errors_tab(self) -> Locator:
        """Get the locator for the 'Sites with errors' tab."""
        return self.slideout.locator('li[role="tab"]', has_text="Sites with errors")

    @property
    def sites_with_changes_tab(self) -> Locator:
        """Get the locator for the 'Sites with changes' tab."""
        return self.slideout.locator('li[role="tab"]', has_text="Sites with changes")

    @property
    def activation_succcess_banner(self) -> Locator:
        return self.slideout.locator("div.cmk-div-activation-result-container")

    def _extract_count_from_label(self, label_locator: Locator, label_name: str) -> int:
        """Get the number in parentheses from a label text."""
        txt = label_locator.text_content()
        if not txt:
            raise AssertionError(f"The '{label_name}' label text is empty!")

        match = re.search(r"\((\d+)\)", txt)
        if not match:
            raise AssertionError(
                f"The '{label_name}' label text '{txt}' does not contain the number in parentheses!"
            )

        return int(match.group(1))

    def total_changes_count(self) -> int:
        """Extract the number of total changes from the label text."""
        return self._extract_count_from_label(self.total_changes_lbl, "Changes")

    def foreign_changes_count(self) -> int:
        """Extract the number of foreign changes from the label text."""
        return self._extract_count_from_label(self.foreign_changes_lbl, "Foreign changes")

    def close(self) -> None:
        self.cmk_page.main_menu.changes_menu().click()
        time.sleep(1)  # wait for the slideout to close
        expect(self.title).not_to_be_visible()
        expect(self.slideout).not_to_be_visible()

    def site_entry(self, site_name: str = "", central: bool = True) -> Locator:
        """Get the locator for the specific site entry in the sites section."""
        text = f"Local site {site_name}" if central else "Remote Testsite"
        return self.slideout.locator("div.cmk-changes-sites-item-wrapper").filter(has_text=text)

    def site_online_status(self, site_entry: Locator) -> Locator:
        """Get the locator for the online status badge of a specific site."""
        return site_entry.locator("div.cmk-badge.cmk-badge-success", has_text="online")

    def site_changes_count(self, site_entry: Locator) -> int:
        """Get the locator of round badge showing the number of changes."""
        txt = site_entry.locator("div.cmk-badge.cmk-badge-warning").text_content()
        if not txt or not txt.isdigit():
            raise AssertionError(
                f"The site entry does not contain a valid changes count badge! Found text: '{txt}'"
            )
        return int(txt)

    def site_entry_checkbox(self, site_entry: Locator) -> Locator:
        """Get the locator of the checkbox to select/deselect a site entry."""
        return site_entry.locator("button[role='checkbox']")

    def is_site_entry_selected(self, site_entry: Locator) -> bool:
        """Check if the site entry checkbox is selected."""
        return self.site_entry_checkbox(site_entry).get_attribute("aria-checked") == "true"

    def ensure_expected_changes_activated(self, expected_changes: int) -> None:
        expect(
            self.slideout.locator(
                "div.cmk-changes-activating-container span",
                has_text="You can safely navigate away",
            )
        ).to_be_visible()
        expect(
            self.slideout.locator(
                "span.cmk-changes-activation-result-title",
                has_text=f"Successfully activated {expected_changes} change",
            )
        ).to_be_visible()

    def activate_changes_strict(self, expected_changes: int) -> None:
        """
        Click the 'Activate pending changes' button and wait for the activation to complete.
        The method performs several assertions to ensure the slideout is in the correct state before
        and after clicking the button.
        These assertions can be disabled by setting the argument 'expected_changes' to 0.
        Args:
            expected_changes: The expected number of changes to be activated.
        """
        if expected_changes:
            logger.info(
                "Activating changes, expecting %s changes to be activated", expected_changes
            )
        else:
            logger.info("Activating changes...")

        expect(self.slideout, "The slideout is not visible!").to_be_visible()

        if expected_changes:
            expect(
                self.no_pending_changes_text,
                f"The banner 'No pending changes' is visible while expecting {expected_changes} changes!",
            ).not_to_be_visible()

        expect(
            self.activate_changes_btn, "The 'Activate Changes' button is not visible!"
        ).to_be_visible()
        expect(
            self.activate_changes_btn, "The 'Activate Changes' button is not enabled!"
        ).to_be_enabled()

        self.activate_changes_btn.click()

        if expected_changes:
            self.ensure_expected_changes_activated(expected_changes)
        else:
            expect(
                self.activation_succcess_banner, "The activation success banner is not visible!"
            ).to_be_visible()
        logging.info("Activation completed!")

    def activate_pending_changes(self) -> None:
        """Activate pending changes and close the slideout afterwards.
        Calls activate_changes_strict with disabled assertions.
        """
        self.activate_changes_strict(expected_changes=0)
        self.close()
