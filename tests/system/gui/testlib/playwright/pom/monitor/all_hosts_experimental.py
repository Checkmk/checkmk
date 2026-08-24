#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from typing import override

from playwright.sync_api import expect, Locator

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class AllHostsExperimental(CmkPage):
    """Represents the Vue page `Monitor -> Overview -> All hosts`.

    This is the Vue-based `cmk-monitoring-all-hosts` web component served by the
    `monitor_all_hosts.py` page, NOT the classic `view.py?view_name=allhost`
    table (see `all_hosts.AllHosts` for that one). The page carries the plain
    "All hosts" title and supersedes the built-in view in the Monitor menu, so
    the menu entry resolves here rather than to the classic table.
    """

    page_title: str = "All hosts"

    @override
    def navigate(self) -> None:
        """Navigate to `Monitor -> Overview -> All hosts`."""
        logger.info("Navigate to '%s' page", self.page_title)
        self.main_menu.monitor_menu(self.page_title, exact=True).click()
        self.page.wait_for_url(url=re.compile(re.escape("monitor_all_hosts.py")), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        # The Vue app must have mounted, not just the page chrome.
        expect(self.app_root).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def app_root(self) -> Locator:
        """Root of the mounted Vue All-hosts app."""
        return self.main_area.locator(".monitoring-all-hosts-app")

    @property
    def table(self) -> Locator:
        """The monitoring table wrapper (present even when no hosts match)."""
        return self.main_area.locator(".monitoring-table")

    @property
    def search_input(self) -> Locator:
        """The host search input in the toolbar."""
        return self.main_area.locator(".monitoring-all-hosts-app__search")

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
        """Toggle the sort of ``column_name`` by clicking its header button.

        A sortable *and* filterable column holds two buttons in the same ``th``, so the sort
        button has to be named; asking the header for "a button" matches both.
        """
        self.column_header(column_name).locator(
            "button.monitoring-table-header__header-button"
        ).click()

    def cell(self, host_name: str, column_name: str) -> Locator:
        """The cell of ``host_name``'s row under the ``column_name`` header.

        The column id is not exposed in the DOM and the visible column set is
        user-configurable, so the position is resolved from the rendered
        headers rather than hard-coded.
        """
        headers = self.table.locator("th")
        labels = [text.strip() for text in headers.all_inner_texts()]
        if column_name not in labels:
            raise AssertionError(f"Column '{column_name}' is not shown; visible: {labels}")
        return self.row_by_host(host_name).locator(
            f"td.monitoring-base-cell:nth-child({labels.index(column_name) + 1})"
        )

    @property
    def search_field(self) -> Locator:
        """The actual ``<input role="searchbox">`` inside the search component."""
        return self.search_input.get_by_role("searchbox")

    def search(self, term: str) -> None:
        """Type ``term`` into the search box and submit it.

        Search is applied server-side: the `q` param is only sent on Enter
        (`CmkSearchInput` emits `search` on `@keydown.enter`), after which the
        table re-fetches. Callers assert the resulting rows with an
        auto-waiting expectation, which absorbs the async refetch.
        """
        field = self.search_field
        field.fill(term)
        field.press("Enter")

    def clear_search(self) -> None:
        """Clear the search box (the clear button re-submits an empty `q`)."""
        self.search_input.locator(".cmk-search-input__clear").click()

    def rows(self) -> Locator:
        """All host data rows of the table.

        Only real data rows carry a ``data-index``; the empty-state row and the
        virtualizer's padding spacers do not, so this excludes them.
        """
        return self.table.locator("tr.monitoring-table__row[data-index]")

    def host_name_cells(self) -> Locator:
        """The host-name cell text spans, in row order.

        The name cell is the only one rendered as a button (it opens the detail
        slide-in), which identifies it without depending on a column position
        that shifts whenever a column is added or hidden. `StringCell` injects
        zero-width spaces into the *displayed* text but keeps the unmodified
        value in the ``title`` attribute, so read names from ``title``.
        """
        return self.rows().locator(
            "td.monitoring-base-cell:has(button.monitoring-base-cell__button) "
            ".monitoring-string-cell__text"
        )

    def host_name_cell(self, index: int) -> Locator:
        """The host-name cell text span at row ``index`` (0-based, in row order).

        ``StringCell`` injects zero-width spaces into the *displayed* text but
        keeps the raw value in the ``title`` attribute, so order assertions read
        the ``title`` (via ``to_have_attribute``) rather than the text content.
        """
        return self.host_name_cells().nth(index)

    def row_by_host(self, name: str) -> Locator:
        """Return the table row whose host-name cell holds ``name`` (exact)."""
        return self.rows().filter(
            has=self.page.locator(f'.monitoring-string-cell__text[title="{name}"]')
        )

    # --- navigation between the classic and the experimental view -------

    @property
    def return_to_classic_view(self) -> Locator:
        """The "Return to classic view" control rendered by the app.

        It is a button that assigns `window.location`, not a link, and it is
        teleported into the page title bar — outside the app root.
        """
        return self.page.locator("button.monitoring-legacy-view-button")

    @property
    def availability_menu_entry(self) -> Locator:
        """The "Availability" entry of the server-rendered page menu."""
        return self.main_area.locator("#menu_entry_availability")

    def open_availability_menu(self) -> None:
        """Open the page menu dropdown holding the Availability entry.

        The clickable trigger is a grandchild of the dropdown container: the
        dropdown wraps a popup-trigger div which holds the anchor.
        """
        self.main_area.locator("#page_menu_dropdown_availability a.popup_trigger").click()

    # --- column picker --------------------------------------------------

    @property
    def column_picker_trigger(self) -> Locator:
        """The column-picker trigger in the shared table toolbar."""
        return self.main_area.locator("button.monitoring-column-picker__trigger")

    @property
    def column_picker_panel(self) -> Locator:
        """The open column-picker panel."""
        return self.main_area.locator(".monitoring-filter-dropdown__panel")

    def column_toggle(self, label: str) -> Locator:
        """A column's show/hide toggle inside the open picker (`aria-pressed`)."""
        return self.column_picker_panel.locator(
            "button.monitoring-filter-column-visibility__row"
        ).filter(has_text=label)

    def apply_column_picker(self) -> None:
        """Commit the picker draft. Toggles are staged until Apply is pressed."""
        self.column_picker_panel.get_by_role("button", name="Apply", exact=True).click()

    @property
    def toolbar_end(self) -> Locator:
        """The right-aligned end of the shared table toolbar."""
        return self.main_area.locator(".monitoring-split-pane__table-toolbar-end")

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

    @property
    def results_count(self) -> Locator:
        """The "Rows matching your criteria" count, shown only while narrowed."""
        return self.main_area.locator("p.monitoring-results-count")

    # --- host detail slide-in -------------------------------------------

    def open_slide_in(self, host_name: str) -> None:
        """Open the host detail slide-in by activating the host name cell."""
        self.row_by_host(host_name).locator("button.monitoring-base-cell__button").click()

    @property
    def slide_in(self) -> Locator:
        """The host detail slide-in container."""
        return self.page.locator(".cmk-slide-in__container").filter(
            has=self.page.locator(".monitoring-slide-in-header")
        )

    @property
    def slide_in_title(self) -> Locator:
        """The host name rendered in the slide-in header."""
        return self.slide_in.locator(".monitoring-slide-in-header__title")

    def slide_in_detail(self, label: str) -> Locator:
        """The value (`dd`) of the overview detail whose label (`dt`) is ``label``."""
        return self.slide_in.locator(
            f'dl.monitoring-overview-detail-list dt:text-is("{label}") + dd'
        )

    def close_slide_in(self) -> None:
        """Close the slide-in via its close button."""
        self.slide_in.locator(".cmk-slide-in-dialog__close").click()

    def host_services_page_url(self, name: str, site_id: str) -> str:
        """Where the "All services" count of ``name`` links to.

        Both the total and the per-state counts open the experimental services page; only the
        per-state ones narrow it with a ``filter`` query param.
        """
        return f"monitor_host_services.py?host={name}&site={site_id}"

    def host_total_services_link(self, name: str) -> Locator:
        """The host's "All services" count cell link (-> services of that host).

        Every services-count cell of the row links to the same page; the per-state ones carry
        a ``filter`` param narrowing it to their state, and the total is the one without.
        """
        return self.row_by_host(name).locator(
            'a.monitoring-base-cell__link[href*="monitor_host_services.py"]:not([href*="filter="])'
        )

    # -- Row selection and the quick actions it arms --------------------------

    def host_checkbox(self, name: str) -> Locator:
        """The row-selection checkbox of one host.

        Named rather than positioned, so a column moving does not silently pick a
        different control. The column only exists for a user who may act on the
        selection.
        """
        return self.main_area.locator().get_by_role(
            "checkbox", name=f"Select host {name}", exact=True
        )

    def tick_host_row(self, name: str) -> None:
        """Tick a host's row-selection checkbox by pressing its cell.

        Named `tick_...` rather than `select_...` because `CmkPage.select_host`
        already means "click the host link" -- one word, two very different acts.

        The checkbox is `pointer-events: none` -- the cell around it carries the click
        handler, so the cell is what a user actually presses and what Playwright can
        act on. The checkbox is still what the control is *found* by, and its
        `aria-checked` is what confirms the press landed, so a renamed or unlabelled
        control fails loudly rather than silently selecting nothing.
        """
        logger.info("Select host '%s'", name)
        checkbox = self.host_checkbox(name)
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

    @property
    def cancel_action(self) -> Locator:
        return self.main_area.locator().get_by_role("button", name="Cancel", exact=True)

    def catalog_panel(self, title: str) -> Locator:
        """A collapsible section of an action form, e.g. Duration or Advanced options."""
        return self.main_area.locator().get_by_role("button", name=title)

    # -- Row limit ------------------------------------------------------------

    @property
    def row_limit(self) -> Locator:
        return self.main_area.locator().get_by_role("combobox", name="Row limit")

    def set_row_limit(self, value: str) -> None:
        logger.info("Set the row limit to '%s'", value)
        self.row_limit.click()
        self.main_area.locator().get_by_role("option", name=value, exact=True).click()

    def ensure_column_shown(self, label: str) -> None:
        """Show a column unless it is already there.

        Column visibility is remembered per user and so survives between tests in a
        module: a blind toggle would hide the column for the second test that ran it.
        """
        if self.column_header(label).count():
            return
        self.column_picker_trigger.click()
        self.column_toggle(label).click()
        self.apply_column_picker()
        expect(self.column_header(label)).to_be_visible()

    def hide_column(self, label: str) -> None:
        self.column_picker_trigger.click()
        self.column_toggle(label).click()
        self.apply_column_picker()

    def row_limit_options(self) -> list[str]:
        """The row limits the page offers, read from the open dropdown."""
        self.row_limit.click()
        options = [
            option.inner_text().strip()
            for option in self.main_area.locator().get_by_role("option").all()
        ]
        self.page.keyboard.press("Escape")
        return options

    def slide_in_action(self, label: str) -> Locator:
        """An action button in the open panel's header."""
        return self.slide_in.get_by_role("button", name=label, exact=True)

    def trigger_slide_in_action(self, label: str) -> None:
        logger.info("Trigger panel action '%s'", label)
        self.slide_in_action(label).click()
