#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import time
from abc import abstractmethod

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)

GOTO_NEXT_STAGE = "Go to the next stage"
GOTO_PREV_STAGE = "Go to the previous stage"


class QuickSetupPage(CmkPage):
    """Base class for Quick Setup pages."""

    page_title = ""

    @abstractmethod
    def navigate(self) -> None:
        pass

    @property
    def overview_mode_button(self) -> Locator:
        return self.main_area.locator().get_by_label("Toggle Overview mode")

    @property
    def guided_mode_button(self) -> Locator:
        return self.main_area.locator().get_by_label("Toggle Guided mode")

    @property
    def is_guided_mode(self) -> bool:
        try:
            expect(self.guided_mode_button).to_have_class(
                r"cmk-button cmk-button--variant-secondary toggle_option selected"
            )
        except ():
            return False

        return True

    @property
    def is_overview_mode(self) -> bool:
        return not self.is_guided_mode

    def ensure_guided_mode(self) -> None:
        if self.is_overview_mode:
            self.guided_mode_button.click()

    def ensure_overview_mode(self) -> None:
        if self.is_guided_mode:
            self.overview_mode_button.click()

    def goto_next_qs_stage(self) -> None:
        self.main_area.locator(".qs-stage--active").get_by_label(GOTO_NEXT_STAGE).click()
        logger.info("Wait for 750ms for proper animation")
        time.sleep(750 / 1000)

    def goto_prev_qs_stage(self) -> None:
        self.main_area.locator(".qs-stage--active").get_by_label(GOTO_PREV_STAGE).click()
        logger.info("Wait for 750ms for proper animation")
        time.sleep(750 / 1000)

    def save_and_test(self) -> None:
        self.main_area.locator(".qs-save-stage__content").get_by_label("Save").first.click()

    def save_and_create_another_rule(self) -> None:
        self.main_area.locator(".qs-save-stage__content").get_by_label("Save").nth(1).click()

    @property
    def editor_slide_in(self) -> Locator:
        return self.main_area.locator().get_by_role("dialog")

    def save_editor_slide_in(self) -> None:
        save = self.editor_slide_in.get_by_role("button", name="Save")
        save.click()
