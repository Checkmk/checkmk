#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from typing import override
from urllib.parse import urljoin

from playwright.sync_api import expect, Locator, Page

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)

# The State column's own tag. `.monitoring-state-tag` alone is not enough: a check's plugin
# output may embed state markers of its own, and those carry the same class inside the Summary
# column. Only the State cell wraps its tag in `.monitoring-state-cell`, and `BaseCell` renders
# just the active one of its abbreviated/spelled-out slots, so this matches exactly one tag.
_STATE_TAG = ".monitoring-state-cell .monitoring-state-tag"

# The state tag spells its label out ("WARNING") or abbreviates it ("WA") depending on how
# wide the rendered column turned out, so a reader of the DOM has to accept either form. Both
# map to the one state name the rest of the API uses.
SERVICE_STATE_LABELS: dict[str, str] = {
    "OK": "OK",
    "WA": "WARN",
    "WARNING": "WARN",
    "CR": "CRIT",
    "CRITICAL": "CRIT",
    "UN": "UNKNOWN",
    "UNKNOWN": "UNKNOWN",
    "PD": "PENDING",
    "PENDING": "PENDING",
}

# Severity rank used to assert state-sorted row order. It mirrors the monitoring core's own
# `state` column, which is what the page sorts on: a service that has never been checked
# carries state 0 there, the same value as OK, so it ranks with OK rather than after UNKNOWN.
# The page orders the State column by the raw state code, so UNKNOWN ranks above CRIT. The
# legacy view ranks CRIT worst instead; which of the two should ship is still open (CMK-37971).
SERVICE_STATE_RANK: dict[str, int] = {
    "PENDING": 0,
    "OK": 0,
    "WARN": 1,
    "CRIT": 2,
    "UNKNOWN": 3,
}


def service_state_of(label: str) -> str:
    """The state name behind a rendered state tag, whichever way it was spelled."""
    try:
        return SERVICE_STATE_LABELS[label.strip()]
    except KeyError:
        raise AssertionError(f"'{label}' is not a state the page renders") from None


class HostServicesExperimental(CmkPage):
    """Represents the Vue page `Services of host <host>` (`monitor_host_services.py`).

    This is the Vue-based `cmk-monitoring-host-services` web component, NOT the
    classic `view.py?view_name=host` table (see `services_of_host.ServicesOfHostPage`
    for that one). The page has no main-menu entry and requires both a `host` and
    a `site` request parameter, so it is reached by URL.
    """

    def __init__(
        self,
        page: Page,
        host_name: str,
        site_id: str,
        navigate_to_page: bool = True,
    ) -> None:
        self.host_name = host_name
        self.site_id = site_id
        self.page_title = f"Services of host {host_name}"
        super().__init__(page=page, navigate_to_page=navigate_to_page)

    @property
    def relative_url(self) -> str:
        """The page's URL relative to the site root, with both mandatory params."""
        return f"monitor_host_services.py?host={self.host_name}&site={self.site_id}"

    @property
    def classic_view_url(self) -> str:
        """The classic view this page links back to."""
        return f"view.py?view_name=host&host={self.host_name}&site={self.site_id}"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        self.page.goto(urljoin(self.page.url, self.relative_url), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        # The page title is byte-identical to the classic view's, so it cannot
        # tell the two apart; the URL and the mounted Vue app can.
        expect(self.page).to_have_url(re.compile(re.escape("monitor_host_services.py")))
        expect(self.app_root).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def app_root(self) -> Locator:
        """Root of the mounted Vue host-services app."""
        return self.main_area.locator(".monitoring-host-services-app")

    @property
    def table(self) -> Locator:
        """The monitoring table wrapper (present even when no services match)."""
        return self.main_area.locator(".monitoring-table")

    def wait_until_settled(self) -> None:
        """Wait until no fetch is in flight.

        Search, sort and filter are all applied server-side; the table marks the
        in-flight refetch with `aria-busy`. Snapshot reads (as opposed to
        auto-waiting expectations) must wait for it to clear first.
        """
        expect(self.table).to_have_attribute("aria-busy", "false")

    def rows(self) -> Locator:
        """All service data rows of the table.

        Only real data rows carry a ``data-index``; the empty-state row and the
        virtualizer's padding spacers do not, so this excludes them.
        """
        return self.table.locator("tr.monitoring-table__row[data-index]")

    def service_name_cells(self) -> Locator:
        """The service-name cell text spans, in row order.

        ``StringCell`` injects zero-width spaces into the *displayed* text but
        keeps the unmodified value in the ``title`` attribute, so read names
        from ``title`` rather than from the text content. The name cell is the
        only one rendered as a button (it opens the detail slide-in), which
        identifies it without depending on a shifting column position.
        """
        return self.rows().locator(
            "td.monitoring-base-cell:has(button.monitoring-base-cell__button) "
            ".monitoring-string-cell__text"
        )

    def rendered_service_names(self) -> list[str]:
        """The raw names of the currently rendered rows, in row order.

        Read in a single evaluation: the page polls every 30s, and a refresh
        landing between per-element reads would detach them mid-iteration.
        """
        names: list[str] = self.service_name_cells().evaluate_all(
            "cells => cells.map(cell => cell.getAttribute('title'))"
        )
        return names

    def rendered_rows(self, *, summary_column: str = "Summary") -> list[dict[str, str]]:
        """Name, state label and summary of every rendered row, read in one evaluation.

        The table is virtualized and the page polls every 30s, so a row looked
        up by name after the name list was read may already have been recycled
        or replaced. Reading the three columns together in a single pass keeps
        the values consistent per row and cannot race either mechanism.
        """
        summary_index = self._column_index(summary_column)
        cells: list[dict[str, str]] = self.rows().evaluate_all(
            """(rows, summaryIndex) => rows.map((row) => {
                const nameCell = row.querySelector(
                    'button.monitoring-base-cell__button .monitoring-string-cell__text'
                )
                const stateTag = row.querySelector(
                    '.monitoring-state-cell .monitoring-state-tag'
                )
                const summaryCell = row.querySelector(
                    `td.monitoring-base-cell:nth-child(${summaryIndex})`
                )
                return {
                    name: nameCell?.getAttribute('title') ?? '',
                    state: (stateTag?.textContent ?? '').trim(),
                    summary: (summaryCell?.textContent ?? '').trim(),
                }
            })""",
            summary_index,
        )
        return cells

    def row_by_service(self, name: str) -> Locator:
        """Return the table row whose service-name cell holds ``name`` (exact)."""
        return self.rows().filter(
            has=self.page.locator(f'.monitoring-string-cell__text[title="{name}"]')
        )

    def state_cell(self, service_name: str) -> Locator:
        """The state tag of ``service_name``'s row (see ``SERVICE_STATE_LABELS``).

        Scoped to the State column: a plugin output may embed its own state
        markers, and those carry the same tag class.
        """
        return self.row_by_service(service_name).locator(_STATE_TAG)

    def state_cells(self) -> Locator:
        """The state tags of all rendered rows, in row order."""
        return self.rows().locator(_STATE_TAG)

    def rendered_states(self) -> list[str]:
        """State names of the currently rendered rows, in row order."""
        return [service_state_of(text) for text in self.state_cells().all_inner_texts()]

    def rendered_state_ranks(self) -> list[int]:
        """Severity ranks of the currently rendered rows, in row order."""
        return [SERVICE_STATE_RANK[state] for state in self.rendered_states()]

    def summary_cell(self, service_name: str) -> Locator:
        """The summary (check output) cell of ``service_name``'s row.

        The column is user-hideable, so its position is resolved from the
        rendered headers rather than hard-coded.
        """
        return self.row_by_service(service_name).locator(
            f"td.monitoring-base-cell:nth-child({self._column_index('Summary')})"
        )

    def _column_index(self, column_name: str) -> int:
        """1-based position of ``column_name`` among the rendered headers."""
        labels = [text.strip() for text in self.table.locator("th").all_inner_texts()]
        if column_name not in labels:
            raise AssertionError(f"Column '{column_name}' is not shown; visible: {labels}")
        return labels.index(column_name) + 1

    # --- search ---------------------------------------------------------

    @property
    def search_input(self) -> Locator:
        """The service search input in the toolbar."""
        return self.main_area.locator(".monitoring-host-services-app__search")

    @property
    def search_field(self) -> Locator:
        """The actual ``<input role="searchbox">`` inside the search component."""
        return self.search_input.get_by_role("searchbox")

    def search(self, term: str) -> None:
        """Type ``term`` into the search box and submit it.

        Search is applied server-side: the query is only sent on Enter, after
        which the table re-fetches. Callers assert the resulting rows with an
        auto-waiting expectation, which absorbs the async refetch.
        """
        field = self.search_field
        field.fill(term)
        field.press("Enter")

    def clear_search(self) -> None:
        """Clear the search box (the clear button re-submits an empty query)."""
        self.search_input.locator(".cmk-search-input__clear").click()

    # --- sorting --------------------------------------------------------

    def column_header(self, name: str) -> Locator:
        """Return the table column header with the given (exact) name.

        Matched on the header's own label element, not on the cell's accessible
        name: a filterable column renders its filter button inside the same
        `th` with an "Filter <column>" aria-label, which folds into that name.
        """
        return self.table.locator("th").filter(
            has=self.page.locator(
                ".monitoring-table-header__label",
                has_text=re.compile(rf"^{re.escape(name)}$"),
            )
        )

    def sort_by(self, column_name: str) -> None:
        """Toggle the sort of ``column_name`` by clicking its header button."""
        self.column_header(column_name).locator(
            "button.monitoring-table-header__header-button"
        ).click()

    # --- column filters -------------------------------------------------

    def open_filter(self, column_name: str) -> Locator:
        """Open ``column_name``'s filter dropdown and return its panel."""
        self.column_header(column_name).locator(
            "button.monitoring-table-header__filter-button"
        ).click()
        return self.filter_panel

    @property
    def filter_panel(self) -> Locator:
        """The open filter dropdown panel."""
        return self.main_area.locator(".monitoring-filter-dropdown__panel")

    def filter_option(self, value: str) -> Locator:
        """A checkbox option inside the open filter panel, by its label."""
        return self.filter_panel.get_by_role("checkbox", name=value, exact=True)

    def apply_filter(self) -> None:
        """Commit the filter draft. Edits are staged until Apply is pressed."""
        self.filter_panel.get_by_role("button", name="Apply", exact=True).click()

    def clear_open_filter(self) -> None:
        """Reset the filter draft; it still needs `apply_filter` to be committed."""
        self.filter_panel.locator(".monitoring-filter-dropdown__clear").click()

    # --- slide-in -------------------------------------------------------

    def open_slide_in(self, service_name: str) -> None:
        """Open the service detail slide-in by activating the service name cell."""
        self.row_by_service(service_name).locator("button.monitoring-base-cell__button").click()

    @property
    def slide_in(self) -> Locator:
        """The service detail slide-in container."""
        return self.page.locator(".cmk-slide-in__container").filter(
            has=self.page.locator(".monitoring-slide-in-header")
        )

    @property
    def slide_in_title(self) -> Locator:
        """The service name rendered in the slide-in header."""
        return self.slide_in.locator(".monitoring-slide-in-header__title")

    @property
    def slide_in_state(self) -> Locator:
        """The service state tag rendered in the slide-in header.

        The header always spells the state out, while the State column may abbreviate it, so
        compare the two through ``service_state_of`` rather than by their raw text.
        """
        return self.slide_in.locator(".monitoring-state-tag")

    def close_slide_in(self) -> None:
        """Close the slide-in via its close button."""
        self.slide_in.locator(".cmk-slide-in-dialog__close").click()

    # --- navigation back to the classic view ----------------------------

    @property
    def return_to_classic_view(self) -> Locator:
        """The "Return to classic view" control rendered by the app.

        It is a button that assigns `window.location`, not a link, and it is
        teleported into the page title bar — outside the app root.
        """
        return self.page.locator("button.monitoring-legacy-view-button")

    # -- Row selection and the quick actions it arms --------------------------

    def service_checkbox(self, name: str) -> Locator:
        """The row-selection checkbox of one service.

        Named rather than positioned; the column only exists for a user who may
        act on the selection.
        """
        return self.main_area.locator().get_by_role(
            "checkbox", name=f"Select service {name}", exact=True
        )

    def tick_service_row(self, name: str) -> None:
        """Tick a service's row-selection checkbox by pressing its cell.

        The checkbox is `pointer-events: none` -- the cell around it carries the click
        handler. The checkbox is still what the control is found by, and its
        `aria-checked` is what confirms the press landed.
        """
        logger.info("Select service '%s'", name)
        checkbox = self.service_checkbox(name)
        checkbox.locator("xpath=ancestor::td[1]").click()
        expect(checkbox).to_have_attribute("aria-checked", "true")

    @property
    def action_bar(self) -> Locator:
        """The toolbar the selection arms."""
        return self.main_area.locator().get_by_role("toolbar")

    def action_button(self, label: str) -> Locator:
        return self.action_bar.get_by_role("button", name=label, exact=True)

    def trigger_action(self, label: str) -> None:
        logger.info("Trigger bulk action '%s'", label)
        self.action_button(label).click()

    # -- The pane an action with a form opens ---------------------------------

    def action_form(self, title: str) -> Locator:
        """The open action form, located by the heading naming the action."""
        return self.main_area.locator().get_by_role("heading", name=title, exact=True)

    @property
    def acknowledge_comment(self) -> Locator:
        return self.main_area.locator().get_by_placeholder("Enter a comment…")

    @property
    def downtime_comment(self) -> Locator:
        return self.main_area.locator().get_by_placeholder("What is the occasion?")

    def submit_action(self, label: str) -> Locator:
        """The form's submit control, which stays disabled while the form is incomplete."""
        return self.main_area.locator().get_by_role("button", name=label, exact=True)

    def form_option(self, label: str) -> Locator:
        """A labelled control inside the open action form."""
        return self.main_area.locator().get_by_text(label, exact=True)
