#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from dataclasses import dataclass
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Page

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.gui_e2e.testlib.playwright.pom.setup.global_settings import GlobalSettings

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

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self._init_locators()

    def _init_locators(self) -> None:
        # Main sections
        self.current_setting = self.main_area.locator().get_by_role("row", name="Current setting")
        self.current_state = self.main_area.locator().get_by_role("row", name="Current state")

        checkbox_locate = "span.checkbox input[type='checkbox']"
        days_locate = "input[name*='days']"
        hours_locate = "input[name*='hours']"
        minutes_locate = "input[name*='minutes']"

        # Maximum session duration section
        self.max_session_duration = self.current_setting.get_by_role(
            "row", name="Maximum session duration"
        )
        self.enforce_reauth = self.max_session_duration.get_by_role(
            "row", name="Enforce re-authentication"
        )
        self.max_session_duration_checkbox = self.max_session_duration.locator(
            "span.checkbox", has_text="Maximum session duration"
        )
        self.max_duration_days = self.enforce_reauth.locator(days_locate)
        self.max_duration_hours = self.enforce_reauth.locator(hours_locate)
        self.max_duration_minutes = self.enforce_reauth.locator(minutes_locate)

        # Advise re-authentication section
        self.advise_reauth = self.max_session_duration.get_by_role(
            "row", name="Advise re-authentication before termination"
        )
        self.advise_reauth_checkbox = self.advise_reauth.locator(checkbox_locate)
        self.advise_reauth_days = self.advise_reauth.locator(days_locate)
        self.advise_reauth_hours = self.advise_reauth.locator(hours_locate)
        self.advise_reauth_minutes = self.advise_reauth.locator(minutes_locate)

        # Idle timeout section
        self.idle_timeout = self.current_setting.get_by_role("row", name="Idle timeout")
        self.idle_timeout_checkbox = self.idle_timeout.locator(checkbox_locate)
        self.idle_timeout_days = self.idle_timeout.locator(days_locate)
        self.idle_timeout_hours = self.idle_timeout.locator(hours_locate)
        self.idle_timeout_minutes = self.idle_timeout.locator(minutes_locate)

    @override
    def navigate(self) -> None:
        """Navigate to the Session Management page."""
        setting_name = "Session management"
        logger.info("Navigate to '%s' setting page", setting_name)
        settings_page = GlobalSettings(self.page)
        settings_page.search_settings(setting_name)
        settings_page.setting_link(setting_name).click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("varname=session_mgmt")), wait_until="load"
        )
        self.validate_page()

    @override
    def validate_page(self) -> None:
        expect(
            self.main_area.locator().get_by_role("cell", name="Session management"),
            message="Session management page heading is not visible",
        ).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def get_max_duration_values(self) -> TimeoutValues:
        """Get all maximum session duration values.

        Returns:
            TimeoutValues instanse representing the maximum session duration.
        """
        return TimeoutValues(
            int(self.max_duration_days.input_value()),
            int(self.max_duration_hours.input_value()),
            int(self.max_duration_minutes.input_value()),
        )

    def set_max_duration_values(self, timeouts: TimeoutValues) -> None:
        """Set all maximum session duration values.

        Args:
            timeouts: TimeoutValues instanse representing the maximum session duration.
        """
        if not self.max_session_duration.get_by_label("Maximum session duration").is_checked():
            self.max_session_duration_checkbox.click()
        self.max_duration_days.fill(str(timeouts.days))
        self.max_duration_hours.fill(str(timeouts.hours))
        self.max_duration_minutes.fill(str(timeouts.minutes))

    def get_advise_reauth_values(self) -> TimeoutValues:
        """Get all advise re-authentication values.

        Returns:
            TimeoutValues instanse representing the advise re-authentication time."""
        return TimeoutValues(
            int(self.advise_reauth_days.input_value()),
            int(self.advise_reauth_hours.input_value()),
            int(self.advise_reauth_minutes.input_value()),
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
            int(self.idle_timeout_days.input_value()),
            int(self.idle_timeout_hours.input_value()),
            int(self.idle_timeout_minutes.input_value()),
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
