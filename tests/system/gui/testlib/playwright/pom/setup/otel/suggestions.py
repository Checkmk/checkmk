#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Page object for the option list of the open dropdown."""

from playwright.sync_api import expect, Locator

from tests.system.gui.testlib.playwright.pom.page import MainArea


class Suggestions:
    """The dropdown teleports its option list to the body, not under its field."""

    def __init__(self, main_area: MainArea) -> None:
        self._main_area = main_area

    @property
    def listbox(self) -> Locator:
        return self._main_area.locator().get_by_role("listbox")

    def search(self, text: str) -> None:
        self.listbox.get_by_role("textbox", name="filter").fill(text)

    def pick(self, title: str) -> None:
        option = self.listbox.get_by_role("option", name=title, exact=True)
        expect(option, f"No suggestion titled {title!r} was offered").to_be_visible()
        option.click()
