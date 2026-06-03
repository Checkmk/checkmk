#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from pathlib import Path
from typing import override

from playwright.sync_api import expect, Locator, Page

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class ManagedRobotsOverview(CmkPage):
    """Represent the page `Setup -> Managed robots`."""

    def __init__(
        self,
        page: Page,
        navigate_to_page: bool = True,
    ) -> None:
        self.page_title = "Managed robots"
        super().__init__(page, navigate_to_page)

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        self.main_menu.setup_menu("Managed robots", show_more=True).click()
        self.page.wait_for_url(
            url=re.compile(re.escape("wato.py?mode=robotmk_managed_robots_overview")),
            wait_until="load",
        )
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        expect(self.create_robot_button).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def create_robot_button(self) -> Locator:
        return self.main_area.get_suggestion("Create robot")

    def robot_row(self, name: str) -> Locator:
        return self.main_area.locator(f"tr:has(td:has-text('{name}'))")

    def delete_robot_button(self, name: str) -> Locator:
        return self.robot_row(name).get_by_role("link", name="Delete")

    @property
    def delete_confirmation_button(self) -> Locator:
        return self.main_area.get_confirmation_popup_button("Delete")

    def delete_robot(self, name: str) -> None:
        logger.info("Deleting robot '%s'", name)
        self.delete_robot_button(name).click()
        self.delete_confirmation_button.click()


class CreateManagedRobot(CmkPage):
    """Represent the page for creating a new managed robot."""

    def __init__(
        self,
        page: Page,
        navigate_to_page: bool = True,
    ) -> None:
        self.page_title = "Create managed robot"
        super().__init__(page, navigate_to_page)

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        ManagedRobotsOverview(self.page).create_robot_button.click(timeout=5000)
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        expect(self.name_input).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def name_input(self) -> Locator:
        return self.main_area.locator().get_by_role("textbox", name="Name", exact=True)

    @property
    def version_label_input(self) -> Locator:
        return self.main_area.locator().get_by_role("textbox", name="Version label")

    @property
    def file_upload_input(self) -> Locator:
        return self.main_area.locator("input[type='file']")

    @property
    def application_name_input(self) -> Locator:
        return self.main_area.locator().get_by_role("textbox", name="Application name")

    @property
    def suite_path_input(self) -> Locator:
        return self.main_area.locator().get_by_role("textbox", name="Relative path to test suite")

    @property
    def conda_manifest_path_input(self) -> Locator:
        return self.main_area.locator().get_by_role("textbox", name="Relative manifest path")

    @property
    def robotmk_manifest_checkbox(self) -> Locator:
        return self.main_area.locator().get_by_role(
            "checkbox", name="Relative path to Robotmk environment manifest"
        )

    @property
    def robotmk_manifest_path_input(self) -> Locator:
        return self.main_area.locator().get_by_role(
            "textbox", name="Relative path to Robotmk environment manifest"
        )

    def enable_robotmk_manifest(self) -> None:
        self.robotmk_manifest_checkbox.check()

    def save(self) -> None:
        logger.info("Saving form")
        self.main_area.get_suggestion("Save").click()

    def fill_and_save(
        self,
        *,
        name: str,
        version_label: str,
        archive_path: Path,
        app_name: str,
        suite_path: str,
        conda_path: str,
        robotmk_path: str,
    ) -> None:
        logger.info("Filling properties: name='%s', version_label='%s'", name, version_label)
        self.name_input.fill(name)
        self.version_label_input.fill(version_label)

        logger.info("Uploading archive '%s'", archive_path.name)
        self.file_upload_input.set_input_files(archive_path)

        logger.info("Filling plan settings: app='%s', suite='%s'", app_name, suite_path)
        self.application_name_input.fill(app_name)
        self.suite_path_input.fill(suite_path)

        logger.info("Filling conda manifest path")
        self.conda_manifest_path_input.fill(conda_path)

        logger.info("Enabling and filling robotmk manifest path")
        self.enable_robotmk_manifest()
        self.robotmk_manifest_path_input.fill(robotmk_path)

        logger.info("Saving the new managed robot")
        self.save()
