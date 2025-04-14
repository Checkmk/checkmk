#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Consolidate objects and functions specific to the page 'Background job' details and overview.

'Background jobs' are accessible using 'Setup'.
"""

import logging
from typing import override

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class BackgroundJobDetails(CmkPage):
    """Represent the page 'Background job details'."""

    @override
    def navigate(self) -> None:
        raise NotImplementedError

    @override
    def validate_page(self) -> None:
        expect(
            self.background_jobs_overview_button,
            message="Expected 'Background jobs overview' button to be enabled!",
        ).to_be_enabled()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def background_jobs_overview_button(self) -> Locator:
        return self.get_link("Background jobs overview")

    @property
    def delete_job_icon(self) -> Locator:
        return self.get_link("Delete this job")

    @property
    def result_retrieve_created_dump_file_icon(self) -> Locator:
        return self._detail_row("Result").get_by_role("link", name="Download")

    @property
    def progress_info_retrieve_created_dump_icon(self) -> Locator:
        return self._detail_row("Progress info").get_by_role("link", name="Download")

    @property
    def job_state(self) -> str:
        """Return the state of the job as text."""
        return self.job_state_locator.inner_text()

    @property
    def job_state_locator(self) -> Locator:
        return self._detail_row("State", exact=True).locator("td")

    @property
    def job_log(self) -> str:
        """Return the job logs as text."""
        return self.job_log_locator.inner_text()

    @property
    def job_log_locator(self) -> Locator:
        return self._detail_row("Progress info", exact=True).locator("td")

    def _detail_row(self, name: str, exact: bool = False) -> Locator:
        """Return the web-element corresponding to a row of detail: 'name'."""
        main_area = self.main_area.locator()
        return self.main_area.locator("tr").filter(
            has=main_area.get_by_role("cell", name=name, exact=exact)
        )
