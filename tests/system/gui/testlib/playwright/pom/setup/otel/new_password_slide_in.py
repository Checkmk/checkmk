#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from playwright.sync_api import expect, Locator


class NewPasswordSlideIn:
    """Represent the 'New password' slide-in opened from any OTel page that
    embeds a password-store selector (the Quick Setup wizard and the
    `Add OpenTelemetry Collector` mode)."""

    title_text = "New password"

    def __init__(self, container: Locator) -> None:
        self._container = container

    def _root(self) -> Locator:
        return self._container.get_by_role("dialog", name=self.title_text)

    @property
    def title(self) -> Locator:
        return self._root().get_by_role("heading", name=self.title_text, exact=True)

    @property
    def save_button(self) -> Locator:
        return self._root().get_by_role("button", name="Save", exact=True)

    @property
    def cancel_button(self) -> Locator:
        return self._root().get_by_role("button", name="Cancel", exact=True)

    @property
    def password_id_textfield(self) -> Locator:
        return self._root().get_by_role("textbox", name="Unique ID")

    @property
    def password_title_textfield(self) -> Locator:
        return self._root().get_by_role("textbox", name="Title")

    @property
    def password_textfield(self) -> Locator:
        return self._root().get_by_role("textbox", name="Password")

    def fill_and_save(self, *, password_id: str, title: str, password: str) -> None:
        expect(
            self.title, "The 'New password' slide-in did not open after clicking 'Create'"
        ).to_be_visible()
        self.password_id_textfield.fill(password_id)
        self.password_title_textfield.fill(title)
        self.password_textfield.fill(password)
        self.save_button.click()
        expect(
            self.title, "The 'New password' slide-in did not close after saving"
        ).not_to_be_visible()
