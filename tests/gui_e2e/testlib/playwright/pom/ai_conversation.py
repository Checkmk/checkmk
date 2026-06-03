#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from re import Pattern
from typing import override

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import LocatorHelper
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.gui_e2e.testlib.playwright.timeouts import TIMEOUT_AI_RESPONSE

logger = logging.getLogger(__name__)


class AiConversationSlideout(LocatorHelper):
    """Represents the AI conversation slideout panel."""

    def __init__(self, cmk_page: CmkPage) -> None:
        self.cmk_page = cmk_page

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
        _loc = self.cmk_page.main_area.locator().locator(selector)
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
        return self.locator().get_by_role("region", name="Explain with AI")

    @property
    def disclaimer(self) -> Locator:
        return self.slideout.get_by_test_id("ai-conversation-disclaimer")

    @property
    def start_button(self) -> Locator:
        return self.disclaimer.get_by_role("button", name="Start AI feature")

    def accept_disclaimer(self) -> None:
        self.start_button.click()
        self.disclaimer.wait_for(state="hidden", timeout=TIMEOUT_AI_RESPONSE)

    @property
    def refresh_button(self) -> Locator:
        return self.slideout.locator(
            ".ai-conversation-element__controls button[title='Regenerate answer']"
        )

    @property
    def loading_indicator(self) -> Locator:
        return self.slideout.get_by_test_id("ai-conversation-header-loading")

    @property
    def answer_content(self) -> Locator:
        return self.slideout.get_by_test_id("ai-markdown-content")

    def wait_for_answer(
        self, expected_text: str | None = None, timeout: float = TIMEOUT_AI_RESPONSE
    ) -> None:
        self.answer_content.wait_for(state="visible", timeout=timeout)
        if expected_text:
            expect(self.answer_content).to_contain_text(expected_text, timeout=timeout)

    @property
    def error_alert(self) -> Locator:
        return self.slideout.get_by_test_id("ai-conversation-alert-error")

    @property
    def action_buttons(self) -> Locator:
        return self.slideout.get_by_test_id("ai-conversation-user-action-container").get_by_role(
            "button"
        )
