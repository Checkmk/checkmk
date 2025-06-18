#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from abc import abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.gui_e2e.testlib.playwright.timeouts import ANIMATION_TIMEOUT
from tests.testlib.common.utils import wait_until

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
            expect(
                self.guided_mode_button,
                message="The class of the 'guided mode' button doesn't match "
                "the pattern '.*selected.*'",
            ).to_have_class(re.compile(".*selected.*"))
        except ():
            return False

        return True

    @property
    def is_overview_mode(self) -> bool:
        return not self.is_guided_mode

    @property
    def active_stage(self) -> Locator:
        """Return the currently active stage in the Quick Setup."""
        return self.main_area.locator(".qs-stage--active")

    @property
    def index_of_active_stage(self) -> int:
        """Return the index of the currently active stage in the Quick Setup."""
        stages = self.main_area.locator(".qs-stage")
        for index, stage in enumerate(stages.all()):
            if "qs-stage--active" in (stage.get_attribute("class") or ""):
                return index

        return -1

    def ensure_guided_mode(self) -> None:
        if self.is_overview_mode:
            self.guided_mode_button.click()

    def ensure_overview_mode(self) -> None:
        if self.is_guided_mode:
            self.overview_mode_button.click()

    @contextmanager
    def wait_for_active_stage_change(self, is_last_stage: bool = False) -> Iterator[None]:
        """Context manager to wait for the active stage to change."""
        initial_stage = self.index_of_active_stage

        yield

        wait_until(
            lambda: self.index_of_active_stage != initial_stage,
            timeout=(10 * ANIMATION_TIMEOUT / 1000),  # Convert ms to seconds and multiply by 10
        )

        if not is_last_stage:
            logger.debug("Wait for animation to complete")
            self.active_stage.element_handle().wait_for_element_state("stable")

    def goto_next_qs_stage(self, is_last_stage: bool = False) -> None:
        with self.wait_for_active_stage_change(is_last_stage):
            self.active_stage.get_by_label(GOTO_NEXT_STAGE).click()

    def goto_prev_qs_stage(self) -> None:
        with self.wait_for_active_stage_change():
            self.active_stage.get_by_label(GOTO_PREV_STAGE).click()

    def save_and_test(self) -> None:
        self.main_area.locator(".qs-save-stage__content").get_by_label("Save").first.click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("wato.py?mode=test_notifications")), wait_until="load"
        )

    def save_and_create_another_rule(self) -> None:
        self.main_area.locator(".qs-save-stage__content").get_by_label("Save").nth(1).click()

    @property
    def editor_slide_in(self) -> Locator:
        return self.main_area.locator().get_by_role("dialog")

    def save_editor_slide_in(self) -> None:
        save = self.editor_slide_in.get_by_role("button", name="Save")
        save.click()
        self.page.wait_for_timeout(ANIMATION_TIMEOUT)
