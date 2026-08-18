#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from dataclasses import dataclass
from typing import override

from playwright.sync_api import expect, Locator, Page

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.page import CmkPage
from tests.system.gui.testlib.playwright.pom.setup.global_settings import GlobalSettings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TimeoutValues:
    days: int
    hours: int
    minutes: int


class SessionManagementPage(CmkPage):
    """Represents the Session Management page in the GUI.

    This page is accessible via the navigation path:
    Setup -> Global settings -> User management -> Session management.
    """

    setting_name = "Session management"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self._init_locators()

    def _time_span_input(self, time_span_title: str, magnitude: str) -> Locator:
        time_span = self.main_area.locator(f"span[role='group'][aria-label='{time_span_title}']")
        return time_span.locator(f"label:has-text('{magnitude}') input")

    def _init_locators(self) -> None:
        main_area = self.main_area.locator()

        # Maximum session duration section
        self.max_session_duration_checkbox = main_area.get_by_role(
            "checkbox", name="Maximum session duration"
        )
        enforce_reauth_title = "Enforce re-authentication after"
        self.max_duration_days = self._time_span_input(enforce_reauth_title, "Days")
        self.max_duration_hours = self._time_span_input(enforce_reauth_title, "Hours")
        self.max_duration_minutes = self._time_span_input(enforce_reauth_title, "Minutes")

        # Advise re-authentication section
        advise_reauth_title = "Advise re-authentication before termination"
        self.advise_reauth_checkbox = main_area.get_by_role("checkbox", name=advise_reauth_title)
        self.advise_reauth_days = self._time_span_input(advise_reauth_title, "Days")
        self.advise_reauth_hours = self._time_span_input(advise_reauth_title, "Hours")
        self.advise_reauth_minutes = self._time_span_input(advise_reauth_title, "Minutes")

        # Idle timeout section
        idle_timeout_title = "Set an individual idle timeout"
        self.idle_timeout_checkbox = main_area.get_by_role("checkbox", name=idle_timeout_title)
        self.idle_timeout_days = self._time_span_input(idle_timeout_title, "Days")
        self.idle_timeout_hours = self._time_span_input(idle_timeout_title, "Hours")
        self.idle_timeout_minutes = self._time_span_input(idle_timeout_title, "Minutes")

    @override
    def navigate(self) -> None:
        """Navigate to the Session Management page."""
        logger.info("Navigate to '%s' setting page", self.setting_name)
        self.navigate_from_global_settings(GlobalSettings(self.page))

    @override
    def validate_page(self) -> None:
        expect(
            self.main_area.locator().get_by_role("checkbox", name="Maximum session duration"),
            message="'Maximum session duration' checkbox is not visible",
        ).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def navigate_from_global_settings(self, global_settings: GlobalSettings) -> None:
        global_settings.search_settings(self.setting_name)
        global_settings.setting_link(self.setting_name).click()
        self.page.wait_for_url(url=re.compile(re.escape("varname=session_mgmt")), wait_until="load")
        self.validate_page()

    @staticmethod
    def _magnitude_value(magnitude_input: Locator) -> int:
        """An empty magnitude input means a zero contribution to the time span."""
        value = magnitude_input.input_value()
        return int(value) if value else 0

    def get_max_duration_values(self) -> TimeoutValues:
        """Get all maximum session duration values.

        Returns:
            TimeoutValues instanse representing the maximum session duration.
        """
        return TimeoutValues(
            self._magnitude_value(self.max_duration_days),
            self._magnitude_value(self.max_duration_hours),
            self._magnitude_value(self.max_duration_minutes),
        )

    def set_max_duration_values(self, timeouts: TimeoutValues) -> None:
        """Set all maximum session duration values.

        Args:
            timeouts: TimeoutValues instanse representing the maximum session duration.
        """
        self.max_session_duration_checkbox.set_checked(True)
        self.max_duration_days.fill(str(timeouts.days))
        self.max_duration_hours.fill(str(timeouts.hours))
        self.max_duration_minutes.fill(str(timeouts.minutes))

    def get_advise_reauth_values(self) -> TimeoutValues:
        """Get all advise re-authentication values.

        Returns:
            TimeoutValues instanse representing the advise re-authentication time."""
        return TimeoutValues(
            self._magnitude_value(self.advise_reauth_days),
            self._magnitude_value(self.advise_reauth_hours),
            self._magnitude_value(self.advise_reauth_minutes),
        )

    def set_advise_reauth_values(self, timeouts: TimeoutValues) -> None:
        """Set all advise re-authentication values.

        Args:
            timeouts: TimeoutValues instanse representing the advise re-authentication time.
        """
        self.advise_reauth_checkbox.set_checked(True)
        self.advise_reauth_days.fill(str(timeouts.days))
        self.advise_reauth_hours.fill(str(timeouts.hours))
        self.advise_reauth_minutes.fill(str(timeouts.minutes))

    def get_idle_timeout_values(self) -> TimeoutValues:
        """Get all idle timeout values.

        Returns:
            TimeoutValues instanse representing the idle timeout.
        """
        return TimeoutValues(
            self._magnitude_value(self.idle_timeout_days),
            self._magnitude_value(self.idle_timeout_hours),
            self._magnitude_value(self.idle_timeout_minutes),
        )

    def set_idle_timeout_values(self, timeouts: TimeoutValues) -> None:
        """Set all idle timeout values.

        Args:
            timeouts: TimeoutValues instanse representing the idle timeout.
        """
        self.idle_timeout_checkbox.set_checked(True)
        self.idle_timeout_days.fill(str(timeouts.days))
        self.idle_timeout_hours.fill(str(timeouts.hours))
        self.idle_timeout_minutes.fill(str(timeouts.minutes))

    def is_at_factory_settings(self) -> bool:
        self.validate_page()
        if not (
            self.max_session_duration_checkbox.is_checked()
            and self.advise_reauth_checkbox.is_checked()
            and self.idle_timeout_checkbox.is_checked()
        ):
            return False
        return (
            self.get_max_duration_values() == TimeoutValues(days=1, hours=0, minutes=0)
            and self.get_advise_reauth_values() == TimeoutValues(days=0, hours=0, minutes=15)
            and self.get_idle_timeout_values() == TimeoutValues(days=0, hours=1, minutes=30)
        )

    def reset_to_default(self) -> None:
        if self.is_at_factory_settings():
            logger.info("Session Management settings are already at factory defaults")
            return
        reset_btn = self.main_area.locator(
            "div.suggestion.enabled.basic a:has-text('Reset to default')"
        )
        expect(reset_btn, message="'Reset to default' button is not visible").to_be_visible()
        reset_btn.click()

        confirmation_dialog = self.main_area.locator().get_by_role(
            "dialog", name="Reset configuration variable to default value?"
        )
        confirmation_dialog.wait_for(state="visible")
        self.main_area.locator().get_by_role("button", name="Reset").click()
        expect(confirmation_dialog).to_be_hidden()

    def save_options(self) -> None:
        self.main_area.get_suggestion("Save").click()
