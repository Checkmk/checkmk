#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Page object for the editor of a telemetry attribute filter."""

import logging
from collections.abc import Callable

from playwright.sync_api import expect, Locator

from tests.system.gui.testlib.playwright.pom.page import MainArea
from tests.system.gui.testlib.playwright.pom.setup.otel.suggestions import Suggestions

logger = logging.getLogger(__name__)


class AttributeFilterEditor:
    """`leave_editing` clicks plain text outside the editor, which differs per hosting form."""

    def __init__(
        self, root: Locator, main_area: MainArea, leave_editing: Callable[[], None]
    ) -> None:
        self.root = root
        self._suggestions = Suggestions(main_area)
        self._leave_editing = leave_editing

    def add_condition(self, attribute_key: str, value: str) -> None:
        """Picking the key from the suggestions sets its kind; "is" is the default operator."""
        logger.info("Filter on '%s' is '%s'", attribute_key, value)
        self.root.get_by_role("button", name="Add condition", exact=True).click()
        self._suggestions.search(attribute_key)
        self._suggestions.pick(attribute_key)
        self._suggestions.search(value)
        self._suggestions.pick(value)
        self._leave_editing()
        expect(
            self.condition(attribute_key, value), "The condition was not applied"
        ).to_be_visible()

    def condition(self, attribute_key: str, value: str) -> Locator:
        return self.root.get_by_role("group", name=f"{attribute_key} is {value}")

    def remove_condition(self, attribute_key: str, value: str) -> None:
        logger.info("Remove the filter on '%s' is '%s'", attribute_key, value)
        condition = self.condition(attribute_key, value)
        condition.get_by_role("button", name="Remove condition", exact=True).click()
        expect(condition, "The condition was not removed").not_to_be_visible()
